import re
from datetime import datetime, timezone
from sqlite3 import IntegrityError

from fastapi import HTTPException

from app.db.session import get_db
from app.models.schemas import (
    UserPublic,
    WorkspaceCreateRequest,
    WorkspaceDetail,
    WorkspaceMember,
    WorkspaceRole,
    WorkspaceSummary,
)


ROLE_ORDER: dict[WorkspaceRole, int] = {"viewer": 1, "editor": 2, "owner": 3}


class WorkspaceService:
    def ensure_default_workspace(self, user: UserPublic) -> WorkspaceSummary:
        existing = self.list_workspaces(user.id)
        if existing:
            return existing[0]
        return self.create_workspace(WorkspaceCreateRequest(name="Demo Workspace"), user)

    def create_workspace(self, payload: WorkspaceCreateRequest, user: UserPublic) -> WorkspaceSummary:
        name = payload.name.strip()
        slug_base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "workspace"
        timestamp = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            slug = slug_base
            suffix = 1
            while conn.execute("SELECT 1 FROM workspaces WHERE slug = ?", (slug,)).fetchone():
                suffix += 1
                slug = f"{slug_base}-{suffix}"
            cursor = conn.execute(
                "INSERT INTO workspaces (name, slug, created_by, created_at) VALUES (?, ?, ?, ?)",
                (name, slug, user.id, timestamp),
            )
            workspace_id = int(cursor.lastrowid)
            conn.execute(
                "INSERT INTO workspace_members (workspace_id, user_id, role, created_at) VALUES (?, ?, 'owner', ?)",
                (workspace_id, user.id, timestamp),
            )
            conn.execute(
                "UPDATE documents SET workspace_id = ? WHERE user_id = ? AND workspace_id IS NULL",
                (workspace_id, user.id),
            )
            conn.execute(
                """
                UPDATE chunks
                SET workspace_id = ?
                WHERE workspace_id IS NULL AND document_id IN (SELECT id FROM documents WHERE workspace_id = ?)
                """,
                (workspace_id, workspace_id),
            )
            conn.commit()
        return self.get_workspace(workspace_id, user.id)

    def list_workspaces(self, user_id: int) -> list[WorkspaceSummary]:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT w.*, wm.role
                FROM workspaces w
                JOIN workspace_members wm ON wm.workspace_id = w.id
                WHERE wm.user_id = ?
                ORDER BY datetime(w.created_at), w.id
                """,
                (user_id,),
            ).fetchall()
        return [self._summary(row) for row in rows]

    def get_workspace(self, workspace_id: int, user_id: int) -> WorkspaceDetail:
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT w.*, wm.role
                FROM workspaces w
                JOIN workspace_members wm ON wm.workspace_id = w.id
                WHERE w.id = ? AND wm.user_id = ?
                """,
                (workspace_id, user_id),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Workspace not found.")
            members = conn.execute(
                """
                SELECT u.id AS user_id, u.name, u.email, wm.role
                FROM workspace_members wm
                JOIN users u ON u.id = wm.user_id
                WHERE wm.workspace_id = ?
                ORDER BY wm.role, u.email
                """,
                (workspace_id,),
            ).fetchall()
        return WorkspaceDetail(
            **self._summary(row).model_dump(),
            members=[
                WorkspaceMember(
                    user_id=int(member["user_id"]),
                    name=str(member["name"]),
                    email=str(member["email"]),
                    role=str(member["role"]),
                )
                for member in members
            ],
        )

    def resolve_workspace_id(self, user_id: int, workspace_id: int | None) -> int:
        if workspace_id is not None:
            self.require_role(user_id, workspace_id, "viewer")
            return workspace_id
        workspaces = self.list_workspaces(user_id)
        if not workspaces:
            raise HTTPException(status_code=404, detail="No workspace is available for this user.")
        return workspaces[0].id

    def require_role(self, user_id: int, workspace_id: int, minimum_role: WorkspaceRole) -> WorkspaceRole:
        with get_db() as conn:
            row = conn.execute(
                "SELECT role FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
                (workspace_id, user_id),
            ).fetchone()
        if not row:
            raise HTTPException(status_code=403, detail="You do not have access to this workspace.")
        role = str(row["role"])
        if ROLE_ORDER[role] < ROLE_ORDER[minimum_role]:
            raise HTTPException(status_code=403, detail=f"{minimum_role.capitalize()} access is required.")
        return role

    def add_member(self, workspace_id: int, owner_id: int, email: str, role: WorkspaceRole) -> WorkspaceDetail:
        self.require_role(owner_id, workspace_id, "owner")
        normalized = email.strip().lower()
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (normalized,)).fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found.")
            try:
                conn.execute(
                    "INSERT INTO workspace_members (workspace_id, user_id, role, created_at) VALUES (?, ?, ?, ?)",
                    (workspace_id, int(user["id"]), role, datetime.now(timezone.utc).isoformat()),
                )
            except IntegrityError as exc:
                raise HTTPException(status_code=409, detail="User is already a workspace member.") from exc
            conn.commit()
        return self.get_workspace(workspace_id, owner_id)

    def patch_member(self, workspace_id: int, owner_id: int, user_id: int, role: WorkspaceRole) -> WorkspaceDetail:
        self.require_role(owner_id, workspace_id, "owner")
        with get_db() as conn:
            conn.execute(
                "UPDATE workspace_members SET role = ? WHERE workspace_id = ? AND user_id = ?",
                (role, workspace_id, user_id),
            )
            conn.commit()
        return self.get_workspace(workspace_id, owner_id)

    def delete_member(self, workspace_id: int, owner_id: int, user_id: int) -> WorkspaceDetail:
        self.require_role(owner_id, workspace_id, "owner")
        if owner_id == user_id:
            raise HTTPException(status_code=400, detail="Owners cannot remove themselves.")
        with get_db() as conn:
            conn.execute(
                "DELETE FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
                (workspace_id, user_id),
            )
            conn.commit()
        return self.get_workspace(workspace_id, owner_id)

    def _summary(self, row) -> WorkspaceSummary:
        return WorkspaceSummary(
            id=int(row["id"]),
            name=str(row["name"]),
            slug=str(row["slug"]),
            role=str(row["role"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )


workspace_service = WorkspaceService()
