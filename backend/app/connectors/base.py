from dataclasses import dataclass


@dataclass
class ConnectorDocument:
    title: str
    content: bytes
    file_name: str
    source_type: str
    source_url: str | None = None
