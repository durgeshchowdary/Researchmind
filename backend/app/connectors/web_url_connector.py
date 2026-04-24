import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

from app.connectors.base import ConnectorDocument


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.title: str | None = None
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self._in_title:
            self.title = cleaned[:180]
        elif self._skip_depth == 0:
            self.parts.append(cleaned)


class WebUrlConnector:
    def fetch(self, url: str) -> ConnectorDocument:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Enter a valid http or https URL.")
        response = requests.get(url, timeout=12, headers={"User-Agent": "ResearchMindConnector/1.0"})
        response.raise_for_status()
        extractor = _TextExtractor()
        extractor.feed(response.text)
        text = "\n".join(extractor.parts)
        if not text.strip():
            raise ValueError("No readable text could be extracted from the webpage.")
        title = extractor.title or parsed.netloc
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-")[:80] or "webpage"
        return ConnectorDocument(
            title=title,
            content=text.encode("utf-8"),
            file_name=f"{slug}.txt",
            source_type="web_url",
            source_url=url,
        )


web_url_connector = WebUrlConnector()
