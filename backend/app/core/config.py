from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    upload_dir: str = str(BASE_DIR / "uploads")
    static_dir: str = str(BASE_DIR / "static")
    max_upload_size_mb: int = 500
    frame_interval_sec: int = 2
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24  # 24시간
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = {"env_file": str(BASE_DIR / ".env"), "env_file_encoding": "utf-8"}


settings = Settings()
