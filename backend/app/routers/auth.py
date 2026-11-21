import time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.database import create_user, get_user_by_email, get_user_by_id, update_user_password
from app.core.security import create_access_token, hash_password, verify_password
from app.middleware.auth import CurrentUser, get_current_user

router = APIRouter()

# 로그인 실패 제한. 같은 이메일로 LOGIN_MAX_FAILS번 연속 실패하면 LOGIN_LOCK_SEC 동안 막는다.
# 서버 메모리에만 두므로 재시작하면 초기화된다. 비밀번호 무차별 대입을 늦추는 용도다.
LOGIN_MAX_FAILS = 5
LOGIN_LOCK_SEC = 10 * 60
_login_fails: dict[str, dict] = {}


def _check_login_lock(email: str) -> None:
    info = _login_fails.get(email)
    if info and info["locked_until"] > time.time():
        remain = int((info["locked_until"] - time.time()) // 60) + 1
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"로그인 시도가 너무 많습니다. {remain}분 후 다시 시도해 주세요.",
        )


def _record_login_fail(email: str) -> None:
    info = _login_fails.setdefault(email, {"count": 0, "locked_until": 0.0})
    if info["locked_until"] and info["locked_until"] <= time.time():
        info["count"] = 0
        info["locked_until"] = 0.0
    info["count"] += 1
    if info["count"] >= LOGIN_MAX_FAILS:
        info["locked_until"] = time.time() + LOGIN_LOCK_SEC
        info["count"] = 0


def _clear_login_fail(email: str) -> None:
    _login_fails.pop(email, None)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(body: SignupRequest):
    if get_user_by_email(body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 사용 중인 이메일입니다.")
    if len(body.password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "비밀번호는 8자 이상이어야 합니다.")

    user = create_user(body.email, hash_password(body.password), body.name)
    return TokenResponse(access_token=create_access_token(user["id"]))


@router.post("/login", response_model=TokenResponse)
def login(body: SignupRequest):
    email = body.email.lower()
    _check_login_lock(email)
    user = get_user_by_email(body.email)
    hashed_password = user.get("hashed_password") if user else None
    if not hashed_password or not verify_password(body.password, hashed_password):
        _record_login_fail(email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다.")

    _clear_login_fail(email)
    return TokenResponse(access_token=create_access_token(user["id"]))


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser = Depends(get_current_user)):
    return UserResponse(id=current_user.id, email=current_user.email, name=current_user.name)


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, current_user: CurrentUser = Depends(get_current_user)):
    if len(body.new_password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "새 비밀번호는 8자 이상이어야 합니다.")

    user = get_user_by_id(current_user.id)
    hashed_password = user.get("hashed_password") if user else None
    if not hashed_password or not verify_password(body.current_password, hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "현재 비밀번호가 올바르지 않습니다.")

    update_user_password(current_user.id, hash_password(body.new_password))
    return {"message": "비밀번호가 변경되었습니다."}
