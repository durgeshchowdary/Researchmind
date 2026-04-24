import hashlib

from app.connectors.web_url_connector import web_url_connector
from app.models.schemas import ConnectorImportResponse, WebUrlImportRequest
from app.services.document_service import document_service
from app.services.indexing_service import indexing_service
from app.services.workspace_service import workspace_service


class ConnectorService:
    def import_web_url(self, payload: WebUrlImportRequest, user_id: int) -> ConnectorImportResponse:
        workspace_id = workspace_service.resolve_workspace_id(user_id, payload.workspace_id)
        workspace_service.require_role(user_id, workspace_id, "editor")
        imported = web_url_connector.fetch(payload.url)
        checksum = f"{workspace_id}_{hashlib.sha256(imported.content).hexdigest()}"
        document = document_service.save_uploaded_document(
            imported.file_name,
            ".txt",
            checksum,
            imported.content,
            user_id,
            workspace_id=workspace_id,
            source_type=imported.source_type,
            source_url=imported.source_url,
        )
        document_service.process_document(document.id)
        indexing_service.rebuild_indexes()
        refreshed = document_service.get_document_detail(document.id, user_id, workspace_id)
        return ConnectorImportResponse(
            document=refreshed,
            task_id=None,
            indexing_mode="synchronous",
            warnings=["Web URL connector uses deterministic HTML text extraction; OAuth connectors are planned."],
        )


connector_service = ConnectorService()
