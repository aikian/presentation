import logging
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"
DEFAULT_SECRET_KEY = "change-me-in-production"
MIN_SECRET_KEY_LEN = 32


def check_secret_key(secret_key: str | None = None) -> None:
    """SECRET_KEY가 기본값이면 RuntimeError를 낸다. 서버 기동 시 호출한다.

    로그인 토큰(JWT)을 이 키로 서명하므로, 기본값 그대로 운영하면 누구나 토큰을
    만들어 남의 계정으로 들어올 수 있다. .env에 32자 이상 임의 문자열을 넣어야 한다.
    """
    key = settings.secret_key if secret_key is None else secret_key
    if not key or key == DEFAULT_SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY가 기본값입니다. backend/.env에 SECRET_KEY를 32자 이상으로 설정하세요. "
            "생성 예) python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    if len(key) < MIN_SECRET_KEY_LEN:
        logging.getLogger(__name__).warning("SECRET_KEY가 %d자보다 짧습니다. 더 긴 값을 권장합니다.", MIN_SECRET_KEY_LEN)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": user_id, "exp": expire}, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    user_id: str = payload.get("sub")
    if user_id is None:
        raise JWTError("sub missing")
    return user_id
