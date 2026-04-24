from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import get_db, initialize_database
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


def test_signup_success(client: TestClient) -> None:
    payload = signup(client, "new@example.com")

    assert payload["access_token"]
    assert payload["user"]["email"] == "new@example.com"


def test_duplicate_signup_blocked(client: TestClient) -> None:
    signup(client, "duplicate@example.com")
    response = client.post(
        "/auth/signup",
        json={"name": "Duplicate", "email": "duplicate@example.com", "password": "password123"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_login_success(client: TestClient) -> None:
    signup(client, "login@example.com")
    response = client.post("/auth/login", json={"email": "login@example.com", "password": "password123"})

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_invalid_password(client: TestClient) -> None:
    signup(client, "bad-password@example.com")
    response = client.post("/auth/login", json={"email": "bad-password@example.com", "password": "wrongpass"})

    assert response.status_code == 401


def test_protected_route_requires_token(client: TestClient) -> None:
    response = client.get("/documents")

    assert response.status_code in {401, 403}


def test_user_cannot_see_another_users_documents(client: TestClient) -> None:
    first = signup(client, "first@example.com")
    second = signup(client, "second@example.com")
    second_user_id = int(second["user"]["id"])
    timestamp = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO documents (
                user_id, title, file_name, file_type, file_path, checksum, raw_text,
                chunk_count, status, status_message, uploaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                second_user_id,
                "Private Paper",
                "private.md",
                "md",
                "private.md",
                "private-checksum",
                "private text",
                0,
                "indexed",
                "Indexed successfully",
                timestamp,
            ),
        )
        conn.commit()

    response = client.get("/documents", headers={"Authorization": f"Bearer {first['access_token']}"})

    assert response.status_code == 200
    assert response.json() == []
