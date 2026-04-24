from datetime import datetime, timedelta, timezone
from sqlite3 import IntegrityError, Row

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.db.session import get_db
from app.models.schemas import AuthResponse, UserPublic


settings = get_settings()
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
DEMO_EMAIL = "demo@researchmind.ai"
DEMO_PASSWORD = "researchmind-demo"


class AuthService:
    def normalize_email(self, email: str) -> str:
        return email.strip().lower()

    def hash_password(self, password: str) -> str:
        # bcrypt has a limit of 72 bytes. We truncate to ensure stability
        # with long passwords and avoid the ValueError from the backend.
        truncated = password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
        return password_context.hash(truncated)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        # We must apply the same truncation during verification
        # so that the hashes remain compatible for long passwords.
        truncated = password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
        return password_context.verify(truncated, hashed_password)

    def create_access_token(self, user_id: int) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes)
        payload = {"sub": str(user_id), "exp": expires_at}
        return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

    def signup(self, name: str, email: str, password: str) -> AuthResponse:
        name_cleaned = name.strip()
        if not name_cleaned:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name is required.")
        normalized_email = self.normalize_email(email)
        if "@" not in normalized_email or "." not in normalized_email:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid email address.")
        if len(password) < 8:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters.")

        created_at = datetime.now(timezone.utc).isoformat()
        try:
            with get_db() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO users (name, email, hashed_password, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name_cleaned, normalized_email, self.hash_password(password), created_at),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        except IntegrityError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.") from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error during signup.") from exc

        if not row:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User record not found after creation.")

        user = self._public_user(row)
        return AuthResponse(access_token=self.create_access_token(user.id), user=user)

    def login(self, email: str, password: str) -> AuthResponse:
        normalized_email = self.normalize_email(email)
        with get_db() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (normalized_email,)).fetchone()
        if not row or not self.verify_password(password, str(row["hashed_password"])):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

        user = self._public_user(row)
        return AuthResponse(access_token=self.create_access_token(user.id), user=user)

    def get_user_by_token(self, token: str) -> UserPublic:
        credentials_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
            user_id = int(str(payload.get("sub") or "0"))
        except (JWTError, ValueError) as exc:
            raise credentials_error from exc

        with get_db() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise credentials_error
        return self._public_user(row)

    def ensure_demo_user(self) -> UserPublic:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (DEMO_EMAIL,)).fetchone()
            if not row:
                created_at = datetime.now(timezone.utc).isoformat()
                cursor = conn.execute(
                    """
                    INSERT INTO users (name, email, hashed_password, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("Demo Researcher", DEMO_EMAIL, self.hash_password(DEMO_PASSWORD), created_at),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
            conn.execute("UPDATE documents SET user_id = ? WHERE user_id IS NULL", (int(row["id"]),))
            conn.commit()
        return self._public_user(row)

    def _public_user(self, row: Row) -> UserPublic:
        return UserPublic(
            id=int(row["id"]),
            name=str(row["name"]),
            email=str(row["email"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )


auth_service = AuthService()
