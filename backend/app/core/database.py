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


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        key = settings.supabase_service_role_key or settings.supabase_key
        if not settings.supabase_url or not key:
            raise RuntimeError("Supabase URL/key is not configured.")
        _supabase = create_client(settings.supabase_url, key)
    return _supabase


def get_user_by_email(email: str) -> dict[str, Any] | None:
    res = (
        get_supabase()
        .table("users")
        .select("id,email,hashed_password,created_at")
        .eq("email", email)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    res = (
        get_supabase()
        .table("users")
        .select("id,email,hashed_password,created_at")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def create_user(email: str, hashed_password: str) -> dict[str, Any]:
    user_id = uuid.uuid4().hex
    payload = {"id": user_id, "email": email, "hashed_password": hashed_password}
    res = get_supabase().table("users").insert(payload).execute()
    return res.data[0] if res.data else payload
