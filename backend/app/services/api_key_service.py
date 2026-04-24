import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.session import get_db
from app.models.schemas import ApiKeyCreateRequest, ApiKeyPublic
from app.services.workspace_service import workspace_service


class ApiKeyService:
    def create_key(self, payload: ApiKeyCreateRequest, user_id: int) -> ApiKeyPublic:
        workspace_id = workspace_service.resolve_workspace_id(user_id, payload.workspace_id)
        workspace_service.require_role(user_id, workspace_id, "owner")
        raw = f"rm_{secrets.token_urlsafe(32)}"
        key_hash = self._hash(raw)
        prefix = raw[:10]
        timestamp = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO api_keys (workspace_id, key_hash, name, prefix, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (workspace_id, key_hash, payload.name.strip(), prefix, timestamp),
            )
            conn.commit()
        created = self._get_by_id(int(cursor.lastrowid))
        payload = created.model_dump()
        payload["api_key"] = raw
        return ApiKeyPublic(**payload)

    def list_keys(self, user_id: int, workspace_id: int | None = None) -> list[ApiKeyPublic]:
        resolved = workspace_service.resolve_workspace_id(user_id, workspace_id)
        workspace_service.require_role(user_id, resolved, "owner")
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM api_keys WHERE workspace_id = ? ORDER BY id DESC", (resolved,)).fetchall()
        return [self._from_row(row) for row in rows]

    def delete_key(self, key_id: int, user_id: int) -> dict[str, str]:
        key = self._get_by_id(key_id)
        workspace_service.require_role(user_id, key.workspace_id, "owner")
        with get_db() as conn:
            conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
            conn.commit()
        return {"status": "deleted"}

    def authenticate(self, raw_key: str) -> int:
        key_hash = self._hash(raw_key)
        with get_db() as conn:
            row = conn.execute("SELECT * FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
            if not row:
                raise HTTPException(status_code=401, detail="Invalid API key.")
            conn.execute(
                "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), int(row["id"])),
            )
            conn.commit()
        return int(row["workspace_id"])

    def _get_by_id(self, key_id: int) -> ApiKeyPublic:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="API key not found.")
        return self._from_row(row)

    def _from_row(self, row) -> ApiKeyPublic:
        return ApiKeyPublic(
            id=int(row["id"]),
            workspace_id=int(row["workspace_id"]),
            name=str(row["name"]),
            prefix=str(row["prefix"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            last_used_at=datetime.fromisoformat(str(row["last_used_at"])) if row["last_used_at"] else None,
        )

    def _hash(self, raw: str) -> str:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


api_key_service = ApiKeyService()
