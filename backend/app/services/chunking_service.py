from app.core.config import get_settings
from app.utils.text import normalize_whitespace, tokenize


settings = get_settings()


class ChunkingService:
    def chunk_text(
        self,
        text: str,
        sections: list[dict[str, int | str | None]] | None = None,
    ) -> list[dict[str, int | str | None]]:
        source_sections = sections or [{"page_number": None, "text": text}]
        chunks: list[dict[str, int | str | None]] = []
        current = ""
        current_tokens: list[str] = []
        current_page: int | None = None

        for section in source_sections:
            page_number = section.get("page_number") if section else None
            raw_text = str(section.get("text") or "")
            normalized_page = int(page_number) if page_number is not None else None
            if current and current_page is not None and normalized_page is not None and current_page != normalized_page:
                chunks.append({"text": current, "token_count": len(current_tokens), "page_number": current_page})
                current = ""
                current_tokens = []
                current_page = None
            paragraphs = [normalize_whitespace(part) for part in raw_text.split("\n") if normalize_whitespace(part)]
            for paragraph in paragraphs:
                paragraph_chunks = self._split_large_paragraph(paragraph)
                for paragraph_chunk in paragraph_chunks:
                    paragraph_tokens = tokenize(paragraph_chunk)
                    if not paragraph_tokens:
                        continue
                    if len(current_tokens) + len(paragraph_tokens) <= settings.chunk_size:
                        current = f"{current}\n\n{paragraph_chunk}".strip()
                        current_tokens.extend(paragraph_tokens)
                        if current_page is None:
                            current_page = normalized_page
                        continue

                    if current:
                        chunks.append(
                            {"text": current, "token_count": len(current_tokens), "page_number": current_page}
                        )

                    overlap_tokens = current_tokens[-settings.chunk_overlap :] if settings.chunk_overlap else []
                    overlap_text = " ".join(overlap_tokens)
                    current = f"{overlap_text}\n\n{paragraph_chunk}".strip() if overlap_text else paragraph_chunk
                    current_tokens = overlap_tokens + paragraph_tokens
                    current_page = normalized_page

        if current:
            chunks.append({"text": current, "token_count": len(current_tokens), "page_number": current_page})

        return chunks

    def _split_large_paragraph(self, paragraph: str) -> list[str]:
        tokens = tokenize(paragraph)
        if len(tokens) <= settings.chunk_size:
            return [paragraph]

        step = max(settings.chunk_size - settings.chunk_overlap, 1)
        windows: list[str] = []
        for start in range(0, len(tokens), step):
            window = tokens[start : start + settings.chunk_size]
            if not window:
                continue
            windows.append(" ".join(window))
            if start + settings.chunk_size >= len(tokens):
                break
        return windows


chunking_service = ChunkingService()
