from pathlib import Path

import fitz

from app.core.exceptions import ExtractionError
from app.utils.text import normalize_document_text


class ExtractionService:
    def extract_text(
        self,
        file_path: Path,
        file_type: str,
    ) -> tuple[str, int | None, list[dict[str, int | str | None]]]:
        if file_type == ".pdf":
            return self._extract_pdf(file_path)
        if file_type in {".txt", ".md"}:
            text = normalize_document_text(file_path.read_text(encoding="utf-8", errors="ignore"))
            return text, None, [{"page_number": None, "text": text}]
        raise ExtractionError(f"Unsupported file type: {file_type}")

    def _extract_pdf(self, file_path: Path) -> tuple[str, int | None, list[dict[str, int | str | None]]]:
        pages: list[dict[str, int | str | None]] = []
        full_text_parts: list[str] = []
        try:
            with fitz.open(file_path) as doc:
                page_count = doc.page_count
                for index, page in enumerate(doc, start=1):
                    page_text = normalize_document_text(page.get_text())
                    if not page_text:
                        continue
                    pages.append({"page_number": index, "text": page_text})
                    full_text_parts.append(page_text)
        except Exception as exc:
            raise ExtractionError(f"Could not read PDF '{file_path.name}': {exc}") from exc

        full_text = normalize_document_text("\n\n".join(full_text_parts))
        return full_text, page_count, pages


extraction_service = ExtractionService()
