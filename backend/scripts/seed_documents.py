import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import initialize_database
from app.services.auth_service import auth_service
from app.services.document_service import document_service


class LocalUploadFile:
    def __init__(self, path: Path) -> None:
        self.filename = path.name
        self._content = path.read_bytes()

    async def read(self) -> bytes:
        return self._content


async def seed() -> None:
    initialize_database()
    demo_user = auth_service.ensure_demo_user()
    seed_dir = Path("data/seed")
    files = [LocalUploadFile(path) for path in seed_dir.iterdir() if path.is_file()]
    await document_service.ingest_files(files, demo_user.id)
    print(f"Seeded {len(files)} file(s) from {seed_dir} for {demo_user.email}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed())
