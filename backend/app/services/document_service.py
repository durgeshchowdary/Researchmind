import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from app.core.exceptions import DuplicateDocumentError, ExtractionError, ResearchMindError
from app.db.session import get_db
from app.models.schemas import ChunkRecord, DocumentDetail, DocumentSummary, StatsSummary
from app.services.chunking_service import chunking_service
from app.services.extraction_service import extraction_service
from app.services.indexing_service import indexing_service
from app.services.workspace_service import workspace_service


logger = logging.getLogger(__name__)


class DocumentService:
    async def ingest_files(
        self,
        files: list[UploadFile],
        user_id: int | None = None,
        workspace_id: int | None = None,
    ) -> tuple[list[DocumentSummary], int, list[str]]:
        ingested: list[DocumentSummary] = []
        duplicate_count = 0
        failures: list[str] = []
        for upload in files:
            file_name = upload.filename or "untitled"
            file_ext = Path(file_name).suffix.lower()
            if file_ext not in {".pdf", ".txt", ".md"}:
                failures.append(f"{file_name}: unsupported file type")
                continue

            content = await upload.read()
            if not content or not content.strip():
                failures.append(f"{file_name}: file is empty")
                continue
            content_checksum = hashlib.sha256(content).hexdigest()
            resolved_workspace_id = workspace_service.resolve_workspace_id(user_id, workspace_id) if user_id is not None else workspace_id
            checksum = f"{resolved_workspace_id or user_id}_{content_checksum}" if user_id is not None else content_checksum
            try:
                persisted = self._upsert_document(file_name, file_ext, checksum, content, user_id, workspace_id=resolved_workspace_id)
                ingested.append(persisted)
            except DuplicateDocumentError:
                duplicate_count += 1
            except ResearchMindError as exc:
                failures.append(f"{file_name}: {exc.message}")
            except Exception as exc:
                logger.exception("Unexpected ingestion failure for %s", file_name)
                failures.append(f"{file_name}: unexpected processing error")

        if ingested or duplicate_count:
            try:
                indexing_service.rebuild_indexes()
            except Exception as exc:
                logger.exception("Index rebuild failed after ingestion")
                failures.append(f"Index rebuild failed: {exc}")
        return ingested, duplicate_count, failures

    def save_uploaded_document(
        self,
        file_name: str,
        file_ext: str,
        checksum: str,
        content: bytes,
        user_id: int | None,
        task_id: str | None = None,
        workspace_id: int | None = None,
        source_type: str = "upload",
        source_url: str | None = None,
    ) -> DocumentSummary:
        return self._upsert_document(
            file_name,
            file_ext,
            checksum,
            content,
            user_id,
            process_immediately=False,
            task_id=task_id,
            workspace_id=workspace_id,
            source_type=source_type,
            source_url=source_url,
        )

    def process_document(self, document_id: int) -> DocumentSummary:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not row:
            raise ResearchMindError("Document not found.", status_code=404)

        file_path = Path(str(row["file_path"]))
        file_ext = f".{str(row['file_type']).lstrip('.')}"
        file_name = str(row["file_name"])
        self._process_document_content(int(row["id"]), file_name, file_ext, file_path)
        with get_db() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return self._summary_from_row(row)

    def _upsert_document(
        self,
        file_name: str,
        file_ext: str,
        checksum: str,
        content: bytes,
        user_id: int | None,
        process_immediately: bool = True,
        task_id: str | None = None,
        workspace_id: int | None = None,
        source_type: str = "upload",
        source_url: str | None = None,
    ) -> DocumentSummary:
        from app.core.config import get_settings

        settings = get_settings()
        settings.ensure_runtime_dirs()
        with get_db() as conn:
            existing = conn.execute(
                "SELECT * FROM documents WHERE checksum = ?",
                (checksum,),
            ).fetchone()
            if existing:
                logger.info("Skipping duplicate document: %s", file_name)
                raise DuplicateDocumentError("A document with the same content already exists.", status_code=409)

            stored_name = f"{checksum}{file_ext}"
            file_path = settings.uploads_path / stored_name
            file_path.write_bytes(content)
            timestamp = datetime.now(timezone.utc).isoformat()
            cursor = conn.execute(
                """
                INSERT INTO documents (
                    user_id, workspace_id, title, file_name, file_type, file_path, checksum, raw_text,
                    authors, year, abstract, keywords,
                    chunk_count, status, status_message, progress, task_id, error_message,
                    page_count, uploaded_at, last_indexed_at, indexed_at, source_type, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    workspace_id,
                    Path(file_name).stem,
                    file_name,
                    file_ext.replace(".", ""),
                    str(file_path),
                    checksum,
                    "",
                    None,
                    None,
                    None,
                    None,
                    0,
                    "uploaded" if process_immediately else "queued",
                    "File saved. Extraction pending." if process_immediately else "Queued for indexing.",
                    0 if process_immediately else 10,
                    task_id,
                    None,
                    None,
                    timestamp,
                    None,
                    None,
                    source_type,
                    source_url,
                ),
            )
            document_id = cursor.lastrowid
            conn.commit()

        if process_immediately:
            self._process_document_content(document_id, file_name, file_ext, file_path)

        with get_db() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
            conn.commit()
            return self._summary_from_row(row)

    def _process_document_content(self, document_id: int, file_name: str, file_ext: str, file_path: Path) -> None:
        try:
            with get_db() as conn:
                conn.execute(
                    "UPDATE documents SET status = 'processing', status_message = ?, progress = ? WHERE id = ?",
                    ("Extracting text.", 25, document_id),
                )
                conn.commit()
            extracted_text, page_count, sections = extraction_service.extract_text(file_path, file_ext)
            if not extracted_text.strip():
                raise ExtractionError(f"No text could be extracted from {file_name}.")
            metadata = self._extract_paper_metadata(Path(file_name).stem, extracted_text)

            with get_db() as conn:
                conn.execute(
                    """
                    UPDATE documents
                    SET title = ?, raw_text = ?, authors = ?, year = ?, abstract = ?, keywords = ?,
                        status = 'extracted', status_message = ?, page_count = ?, progress = ?
                    WHERE id = ?
                    """,
                    (
                        metadata["title"],
                        extracted_text,
                        metadata["authors"],
                        metadata["year"],
                        metadata["abstract"],
                        metadata["keywords"],
                        "Text extracted successfully.",
                        page_count,
                        55,
                        document_id,
                    ),
                )
                conn.commit()

            chunks = chunking_service.chunk_text(extracted_text, sections)
            if not chunks:
                raise ExtractionError(f"No chunks could be created from {file_name}.")
            with get_db() as conn:
                conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
                conn.executemany(
                    """
                    INSERT INTO chunks (document_id, workspace_id, chunk_index, text, token_count, page_number)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            document_id,
                            self._workspace_id_for_document(document_id),
                            index,
                            str(chunk["text"]),
                            int(chunk["token_count"]),
                            chunk.get("page_number"),
                        )
                        for index, chunk in enumerate(chunks)
                    ],
                )
                conn.execute(
                    """
                    UPDATE documents
                    SET chunk_count = ?, status = 'chunked', status_message = ?, progress = ?
                    WHERE id = ?
                    """,
                    (len(chunks), "Document chunked and ready for indexing.", 75, document_id),
                )
                conn.commit()
        except ExtractionError as exc:
            self._mark_failed(document_id, exc.message)
            raise
        except Exception as exc:
            logger.exception("Document processing failed for %s", file_name)
            self._mark_failed(document_id, "Unexpected processing error")
            raise ResearchMindError(
                f"Processing failed for {file_name}: unexpected processing error",
                status_code=500,
            ) from exc

    def list_documents(self, user_id: int | None = None, workspace_id: int | None = None) -> list[DocumentSummary]:
        with get_db() as conn:
            if user_id is None and workspace_id is None:
                rows = conn.execute("SELECT * FROM documents ORDER BY datetime(uploaded_at) DESC").fetchall()
            elif workspace_id is not None:
                params: tuple[int, ...]
                query = "SELECT * FROM documents WHERE workspace_id = ?"
                params = (workspace_id,)
                if user_id is not None:
                    query += " AND user_id = ?"
                    params = (workspace_id, user_id)
                rows = conn.execute(f"{query} ORDER BY datetime(uploaded_at) DESC", params).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM documents WHERE user_id = ? ORDER BY datetime(uploaded_at) DESC",
                    (user_id,),
                ).fetchall()
        return [self._summary_from_row(row) for row in rows]

    def get_document_detail(
        self,
        document_id: int,
        user_id: int | None = None,
        workspace_id: int | None = None,
    ) -> DocumentDetail | None:
        with get_db() as conn:
            if user_id is not None and workspace_id is not None:
                row = conn.execute(
                    "SELECT * FROM documents WHERE id = ? AND user_id = ? AND workspace_id = ?",
                    (document_id, user_id, workspace_id),
                ).fetchone()
            elif user_id is not None:
                row = conn.execute(
                    "SELECT * FROM documents WHERE id = ? AND user_id = ?",
                    (document_id, user_id),
                ).fetchone()
            elif workspace_id is not None:
                row = conn.execute("SELECT * FROM documents WHERE id = ? AND workspace_id = ?", (document_id, workspace_id)).fetchone()
            else:
                row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
            if not row:
                return None
            chunks = conn.execute(
                "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index",
                (document_id,),
            ).fetchall()

        return DocumentDetail(
            **self._summary_from_row(row).model_dump(),
            chunks=[
                ChunkRecord(
                    id=int(chunk["id"]),
                    document_id=int(chunk["document_id"]),
                    chunk_index=int(chunk["chunk_index"]),
                    text=str(chunk["text"]),
                    token_count=int(chunk["token_count"]),
                    page_number=int(chunk["page_number"]) if chunk["page_number"] is not None else None,
                )
                for chunk in chunks
            ],
        )

    def get_chunk_rows(
        self,
        chunk_ids: list[int] | None = None,
        document_id: int | None = None,
        user_id: int | None = None,
        workspace_id: int | None = None,
    ) -> dict[int, dict]:
        if not chunk_ids and not document_id:
            return {}
        conditions: list[str] = []
        params: list[int] = []
        if chunk_ids:
            placeholders = ",".join("?" for _ in chunk_ids)
            conditions.append(f"c.id IN ({placeholders})")
            params.extend(chunk_ids)
        if document_id is not None:
            conditions.append("c.document_id = ?")
            params.append(document_id)
        if user_id is not None:
            conditions.append("d.user_id = ?")
            params.append(user_id)
        if workspace_id is not None:
            conditions.append("d.workspace_id = ?")
            params.append(workspace_id)
        with get_db() as conn:
            rows = conn.execute(
                f"""
                SELECT c.id, c.document_id, c.chunk_index, c.text, c.page_number, d.title, d.status, d.checksum, d.workspace_id, d.source_url
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE {' AND '.join(conditions)}
                """,
                tuple(params),
            ).fetchall()
        return {
            int(row["id"]): {
                "chunk_id": int(row["id"]),
                "document_id": int(row["document_id"]),
                "chunk_index": int(row["chunk_index"]),
                "text": str(row["text"]),
                "page_number": int(row["page_number"]) if row["page_number"] is not None else None,
                "document_title": str(row["title"]),
                "document_status": str(row["status"]),
                "document_checksum": str(row["checksum"]),
                "workspace_id": int(row["workspace_id"]) if row["workspace_id"] is not None else None,
                "source_url": str(row["source_url"]) if row["source_url"] else None,
            }
            for row in rows
        }

    def get_stats(self, user_id: int | None = None, workspace_id: int | None = None) -> StatsSummary:
        with get_db() as conn:
            query = """
                SELECT
                    COUNT(*) AS document_count,
                    SUM(CASE WHEN status = 'indexed' THEN 1 ELSE 0 END) AS indexed_document_count,
                    COALESCE(SUM(chunk_count), 0) AS chunk_count,
                    MAX(last_indexed_at) AS last_indexed_at
                FROM documents
            """
            params: tuple[int, ...] = ()
            filters: list[str] = []
            raw_params: list[int] = []
            if user_id is not None:
                filters.append("user_id = ?")
                raw_params.append(user_id)
            if workspace_id is not None:
                filters.append("workspace_id = ?")
                raw_params.append(workspace_id)
            if filters:
                query += " WHERE " + " AND ".join(filters)
                params = tuple(raw_params)
            row = conn.execute(query, params).fetchone()
        return StatsSummary(
            document_count=int(row["document_count"] or 0),
            indexed_document_count=int(row["indexed_document_count"] or 0),
            chunk_count=int(row["chunk_count"] or 0),
            last_indexed_at=datetime.fromisoformat(str(row["last_indexed_at"]))
            if row["last_indexed_at"]
            else None,
        )

    def _summary_from_row(self, row) -> DocumentSummary:
        return DocumentSummary(
            id=int(row["id"]),
            workspace_id=int(row["workspace_id"]) if "workspace_id" in row.keys() and row["workspace_id"] is not None else None,
            title=str(row["title"]),
            file_name=str(row["file_name"]),
            file_type=str(row["file_type"]),
            authors=self._split_metadata_list(row["authors"] if "authors" in row.keys() else None),
            year=int(row["year"]) if "year" in row.keys() and row["year"] is not None else None,
            abstract=str(row["abstract"]) if "abstract" in row.keys() and row["abstract"] else None,
            keywords=self._split_metadata_list(row["keywords"] if "keywords" in row.keys() else None),
            chunk_count=int(row["chunk_count"]),
            uploaded_at=datetime.fromisoformat(str(row["uploaded_at"])),
            last_indexed_at=datetime.fromisoformat(str(row["last_indexed_at"]))
            if row["last_indexed_at"]
            else None,
            checksum=str(row["checksum"]),
            status=str(row["status"]),
            status_message=str(row["status_message"]) if row["status_message"] else None,
            page_count=int(row["page_count"]) if row["page_count"] is not None else None,
            progress=int(row["progress"]) if "progress" in row.keys() and row["progress"] is not None else 0,
            task_id=str(row["task_id"]) if "task_id" in row.keys() and row["task_id"] else None,
            error_message=str(row["error_message"]) if "error_message" in row.keys() and row["error_message"] else None,
            indexed_at=datetime.fromisoformat(str(row["indexed_at"]))
            if "indexed_at" in row.keys() and row["indexed_at"]
            else None,
            source_type=str(row["source_type"]) if "source_type" in row.keys() and row["source_type"] else "upload",
            source_url=str(row["source_url"]) if "source_url" in row.keys() and row["source_url"] else None,
        )

    def _extract_paper_metadata(self, fallback_title: str, text: str) -> dict[str, str | int | None]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = self._guess_title(fallback_title, lines)
        authors = self._guess_authors(lines, title)
        year = self._guess_year(text)
        abstract = self._guess_section_text(text, "abstract", ["keywords", "index terms", "introduction", "1 introduction"])
        keywords = self._guess_keywords(text)
        return {
            "title": title,
            "authors": "; ".join(authors) if authors else None,
            "year": year,
            "abstract": abstract,
            "keywords": "; ".join(keywords) if keywords else None,
        }

    def _guess_title(self, fallback_title: str, lines: list[str]) -> str:
        for line in lines[:12]:
            normalized = line.strip(" .:-")
            lower = normalized.lower()
            if 8 <= len(normalized) <= 180 and lower not in {"abstract", "introduction", "keywords"}:
                if not re.search(r"^(vol\.|issn|isbn|doi:|http|www\.)", lower):
                    return normalized
        return fallback_title

    def _guess_authors(self, lines: list[str], title: str) -> list[str]:
        try:
            title_index = next(index for index, line in enumerate(lines[:12]) if line.strip(" .:-") == title)
        except StopIteration:
            title_index = 0
        candidates = lines[title_index + 1 : title_index + 5]
        for candidate in candidates:
            lower = candidate.lower()
            if any(marker in lower for marker in ["abstract", "university", "department", "doi", "http", "conference"]):
                continue
            if re.search(r"\d", candidate):
                continue
            if "," in candidate or " and " in lower or len(candidate.split()) <= 10:
                authors = re.split(r",|;|\band\b", candidate)
                cleaned = [author.strip(" ,;") for author in authors if len(author.strip(" ,;")) >= 3]
                if cleaned:
                    return cleaned[:8]
        return []

    def _guess_year(self, text: str) -> int | None:
        matches = [int(match) for match in re.findall(r"\b(19\d{2}|20\d{2})\b", text[:5000])]
        return max(matches) if matches else None

    def _guess_section_text(self, text: str, start_label: str, end_labels: list[str]) -> str | None:
        normalized = text.replace("\r\n", "\n")
        start = re.search(rf"(?is)\b{re.escape(start_label)}\b\s*[:.\-]?\s*", normalized)
        if not start:
            return None
        section_start = start.end()
        section_end = len(normalized)
        for label in end_labels:
            match = re.search(rf"(?is)\n\s*{re.escape(label)}\b\s*[:.\-]?", normalized[section_start:])
            if match:
                section_end = section_start + match.start()
                break
        section = re.sub(r"\s+", " ", normalized[section_start:section_end]).strip()
        if not section:
            return None
        return section[:1400]

    def _guess_keywords(self, text: str) -> list[str]:
        match = re.search(r"(?is)\b(?:keywords|index terms)\b\s*[:.\-]?\s*(.+?)(?:\n\s*\n|\n\s*(?:introduction|1 introduction)\b)", text)
        if not match:
            return []
        raw_keywords = re.split(r",|;|\u2022|\|", match.group(1))
        return [keyword.strip(" .:-\n\t") for keyword in raw_keywords if 2 <= len(keyword.strip(" .:-\n\t")) <= 60][:12]

    def _split_metadata_list(self, value: object) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in str(value).split(";") if item.strip()]

    def _mark_failed(self, document_id: int, message: str) -> None:
        with get_db() as conn:
            conn.execute(
                """
                UPDATE documents
                SET status = 'failed', status_message = ?, error_message = ?, progress = 100
                WHERE id = ?
                """,
                (message, message, document_id),
            )
            conn.commit()

    def _workspace_id_for_document(self, document_id: int) -> int | None:
        with get_db() as conn:
            row = conn.execute("SELECT workspace_id FROM documents WHERE id = ?", (document_id,)).fetchone()
        return int(row["workspace_id"]) if row and row["workspace_id"] is not None else None


document_service = DocumentService()
