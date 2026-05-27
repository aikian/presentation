from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.database import create_user, get_user_by_email
from app.core.security import create_access_token, hash_password, verify_password
from app.middleware.auth import CurrentUser, get_current_user

router = APIRouter()


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


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(body: SignupRequest):
    if get_user_by_email(body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 사용 중인 이메일입니다.")
    if len(body.password) < 6:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "비밀번호는 6자 이상이어야 합니다.")

    user = create_user(body.email, hash_password(body.password), body.name)
    return TokenResponse(access_token=create_access_token(user["id"]))


@router.post("/login", response_model=TokenResponse)
def login(body: SignupRequest):
    user = get_user_by_email(body.email)
    hashed_password = user.get("hashed_password") if user else None
    if not hashed_password or not verify_password(body.password, hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다.")

    return TokenResponse(access_token=create_access_token(user["id"]))


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser = Depends(get_current_user)):
    return UserResponse(id=current_user.id, email=current_user.email, name=current_user.name)
