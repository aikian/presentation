from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pathlib import Path
from typing import Any
import uuid

from supabase import create_client, Client

from app.core.config import settings

DB_PATH = Path(__file__).resolve().parents[2] / "presentationcoach.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_supabase: Client | None = None

_USER_COLUMNS = "id,email,hashed_password,created_at"
_USER_COLUMNS_WITH_NAME = f"{_USER_COLUMNS},name"


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        key = settings.supabase_service_role_key or settings.supabase_key
        if not settings.supabase_url or not key:
            raise RuntimeError("Supabase URL/key is not configured.")
        _supabase = create_client(settings.supabase_url, key)
    return _supabase


def _is_missing_name_column(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "users.name" in message
        or (
            "users" in message
            and "name" in message
            and ("does not exist" in message or "schema cache" in message)
        )
    )


def _fetch_user_by(column: str, value: str) -> dict[str, Any] | None:
    try:
        res = (
            get_supabase()
            .table("users")
            .select(_USER_COLUMNS_WITH_NAME)
            .eq(column, value)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        if not _is_missing_name_column(exc):
            raise
        res = (
            get_supabase()
            .table("users")
            .select(_USER_COLUMNS)
            .eq(column, value)
            .limit(1)
            .execute()
        )

    if not res.data:
        return None

    user = res.data[0]
    user.setdefault("name", None)
    return user


def get_user_by_email(email: str) -> dict[str, Any] | None:
    return _fetch_user_by("email", email)


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    return _fetch_user_by("id", user_id)


def create_user(email: str, hashed_password: str, name: str | None = None) -> dict[str, Any]:
    user_id = uuid.uuid4().hex
    payload: dict[str, Any] = {"id": user_id, "email": email, "hashed_password": hashed_password}
    if name:
        payload["name"] = name

    try:
        res = get_supabase().table("users").insert(payload).execute()
    except Exception as exc:
        if "name" not in payload or not _is_missing_name_column(exc):
            raise
        payload.pop("name")
        res = get_supabase().table("users").insert(payload).execute()

    payload.setdefault("name", None)
    if not res.data:
        return payload

    user = res.data[0]
    user.setdefault("name", None)
    return user
