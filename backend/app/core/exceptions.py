class ResearchMindError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ExtractionError(ResearchMindError):
    pass


class EmbeddingUnavailableError(ResearchMindError):
    pass


class DuplicateDocumentError(ResearchMindError):
    pass
