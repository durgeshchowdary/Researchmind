import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.core.config import get_settings


settings = get_settings()


def initialize_database() -> None:
    settings.ensure_runtime_dirs()
    with sqlite3.connect(settings.database_file) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workspace_members (
                workspace_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('owner', 'editor', 'viewer')),
                created_at TEXT NOT NULL,
                PRIMARY KEY(workspace_id, user_id),
                FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                checksum TEXT NOT NULL UNIQUE,
                raw_text TEXT NOT NULL,
                authors TEXT,
                year INTEGER,
                abstract TEXT,
                keywords TEXT,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'uploaded',
                status_message TEXT,
                progress INTEGER NOT NULL DEFAULT 0,
                task_id TEXT,
                error_message TEXT,
                page_count INTEGER,
                uploaded_at TEXT NOT NULL,
                last_indexed_at TEXT,
                indexed_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        _ensure_column(conn, "documents", "user_id", "INTEGER")
        _ensure_column(conn, "documents", "workspace_id", "INTEGER")
        _ensure_column(conn, "documents", "status", "TEXT NOT NULL DEFAULT 'uploaded'")
        _ensure_column(conn, "documents", "status_message", "TEXT")
        _ensure_column(conn, "documents", "progress", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "documents", "task_id", "TEXT")
        _ensure_column(conn, "documents", "error_message", "TEXT")
        _ensure_column(conn, "documents", "page_count", "INTEGER")
        _ensure_column(conn, "documents", "indexed_at", "TEXT")
        _ensure_column(conn, "documents", "authors", "TEXT")
        _ensure_column(conn, "documents", "year", "INTEGER")
        _ensure_column(conn, "documents", "abstract", "TEXT")
        _ensure_column(conn, "documents", "keywords", "TEXT")
        _ensure_column(conn, "documents", "source_type", "TEXT NOT NULL DEFAULT 'upload'")
        _ensure_column(conn, "documents", "source_url", "TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                token_count INTEGER NOT NULL,
                page_number INTEGER,
                FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )
        _ensure_column(conn, "chunks", "page_number", "INTEGER")
        _ensure_column(conn, "chunks", "workspace_id", "INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON chunks(chunk_index)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_workspace_id ON documents(workspace_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_workspace_id ON chunks(workspace_id)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS indexing_tasks (
                task_id TEXT PRIMARY KEY,
                document_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                indexing_mode TEXT NOT NULL DEFAULT 'synchronous',
                FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )
        _ensure_column(conn, "indexing_tasks", "workspace_id", "INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_indexing_tasks_document_id ON indexing_tasks(document_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_indexing_tasks_workspace_id ON indexing_tasks(workspace_id)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS observability_metrics (
                name TEXT PRIMARY KEY,
                value REAL NOT NULL DEFAULT 0,
                count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS eval_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS eval_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eval_set_id INTEGER NOT NULL,
                workspace_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                expected_answer TEXT,
                expected_terms TEXT,
                expected_document_ids TEXT,
                expected_citation_chunk_ids TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(eval_set_id) REFERENCES eval_sets(id) ON DELETE CASCADE,
                FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS eval_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eval_set_id INTEGER NOT NULL,
                workspace_id INTEGER NOT NULL,
                summary_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(eval_set_id) REFERENCES eval_sets(id) ON DELETE CASCADE,
                FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS eval_run_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                question_id INTEGER,
                result_json TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES eval_runs(id) ON DELETE CASCADE,
                FOREIGN KEY(question_id) REFERENCES eval_questions(id) ON DELETE SET NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS index_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                document_id INTEGER,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                key_hash TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                prefix TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_used_at TEXT,
                FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_chunks_document_chunk_unique ON chunks(document_id, chunk_index)"
        )
        conn.commit()


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_definition: str) -> None:
    existing_columns = {
        row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in existing_columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def database_ready() -> bool:
    return settings.database_file.exists()


@contextmanager
def get_db():
    conn = sqlite3.connect(settings.database_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()
