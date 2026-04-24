from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import get_db
from app.db.session import initialize_database
from app.main import app
from app.services.auth_service import auth_service


@pytest.fixture()
def client():
    test_root = Path("data/test-runs") / uuid4().hex
    settings = get_settings()
    settings.database_path = str(test_root / "researchmind-test.db")
    settings.uploads_dir = str(test_root / "uploads")
    settings.index_dir = str(test_root / "indexes")
    settings.temp_dir = str(test_root / "tmp")
    settings.seed_dir = str(test_root / "seed")
    settings.jwt_secret = "test-secret"
    initialize_database()
    auth_service.ensure_demo_user()
    with TestClient(app) as test_client:
        yield test_client


def signup(client: TestClient, email: str, password: str = "password123") -> dict:
    response = client.post(
        "/auth/signup",
        json={"name": "Test User", "email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def auth_header(payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


def first_workspace(client: TestClient, user: dict) -> dict:
    response = client.get("/workspaces", headers=auth_header(user))
    assert response.status_code == 200
    return response.json()[0]


def test_workspace_isolation_and_role_permissions(client: TestClient) -> None:
    owner = signup(client, "owner-platform@example.com")
    viewer = signup(client, "viewer-platform@example.com")
    workspace = first_workspace(client, owner)

    add_response = client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": viewer["user"]["email"], "role": "viewer"},
        headers=auth_header(owner),
    )
    assert add_response.status_code == 200

    blocked_upload = client.post(
        "/documents/upload",
        data={"workspace_id": str(workspace["id"])},
        files={"files": ("note.txt", b"viewer cannot upload", "text/plain")},
        headers=auth_header(viewer),
    )
    assert blocked_upload.status_code == 403

    private_workspace = first_workspace(client, viewer)
    timestamp = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO documents (
                user_id, workspace_id, title, file_name, file_type, file_path, checksum, raw_text,
                chunk_count, status, status_message, uploaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(viewer["user"]["id"]),
                int(private_workspace["id"]),
                "Private Workspace Doc",
                "private.txt",
                "txt",
                "private.txt",
                "private-workspace-checksum",
                "private text",
                0,
                "indexed",
                "Indexed",
                timestamp,
            ),
        )
        conn.commit()

    documents = client.get("/documents", headers=auth_header(owner))
    assert documents.status_code == 200
    assert all(item["title"] != "Private Workspace Doc" for item in documents.json())


def test_benchmark_builder_and_run(client: TestClient) -> None:
    user = signup(client, "bench-platform@example.com")
    workspace = first_workspace(client, user)
    created = client.post(
        "/evaluation/sets",
        json={"workspace_id": workspace["id"], "name": "Smoke Benchmark"},
        headers=auth_header(user),
    )
    assert created.status_code == 200
    eval_set = created.json()

    question = client.post(
        f"/evaluation/sets/{eval_set['id']}/questions",
        json={"question": "What is retrieval?", "expected_terms": ["retrieval"]},
        headers=auth_header(user),
    )
    assert question.status_code == 200

    run = client.post(f"/evaluation/sets/{eval_set['id']}/run", headers=auth_header(user))
    assert run.status_code == 200
    assert run.json()["summary"]["dataset_size"] == 1


def test_retrieval_playground_index_status_connector_and_api_key(client: TestClient, monkeypatch) -> None:
    user = signup(client, "platform-api@example.com")
    workspace = first_workspace(client, user)

    playground = client.post(
        "/retrieval/playground",
        json={"workspace_id": workspace["id"], "query": "retrieval", "top_k": 3, "pipelines": ["bm25", "hybrid_reranked"]},
        headers=auth_header(user),
    )
    assert playground.status_code == 200
    assert {item["pipeline"] for item in playground.json()["pipelines"]} == {"bm25", "hybrid_reranked"}

    status = client.get(f"/workspaces/{workspace['id']}/index/status", headers=auth_header(user))
    assert status.status_code == 200
    assert status.json()["workspace_id"] == workspace["id"]

    from app.models.schemas import ConnectorImportResponse, DocumentSummary
    from app.services.connector_service import connector_service

    monkeypatch.setattr(
        connector_service,
        "import_web_url",
        lambda payload, user_id: ConnectorImportResponse(
            document=DocumentSummary(
                id=999,
                workspace_id=workspace["id"],
                title="Imported Page",
                file_name="imported-page.txt",
                file_type="txt",
                chunk_count=0,
                uploaded_at=datetime.now(timezone.utc),
                last_indexed_at=None,
                checksum="connector-checksum",
                status="indexed",
                source_type="web_url",
                source_url=payload.url,
            ),
            indexing_mode="synchronous",
            warnings=["mock connector"],
        ),
    )
    imported = client.post(
        "/connectors/web-url/import",
        json={"workspace_id": workspace["id"], "url": "https://example.com/article"},
        headers=auth_header(user),
    )
    assert imported.status_code == 200
    assert imported.json()["document"]["source_type"] == "web_url"

    key = client.post(
        "/api-keys",
        json={"workspace_id": workspace["id"], "name": "Smoke key"},
        headers=auth_header(user),
    )
    assert key.status_code == 200
    raw_key = key.json()["api_key"]
    retrieve = client.post(
        "/api/retrieve",
        json={"query": "hybrid retrieval", "limit": 3},
        headers={"X-API-Key": raw_key},
    )
    assert retrieve.status_code == 200
    assert retrieve.json()["query"] == "hybrid retrieval"
