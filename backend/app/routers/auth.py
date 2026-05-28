from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.database import create_user, get_user_by_email, get_user_by_id, update_user_password
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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


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


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, current_user: CurrentUser = Depends(get_current_user)):
    if len(body.new_password) < 6:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "새 비밀번호는 6자 이상이어야 합니다.")

    user = get_user_by_id(current_user.id)
    hashed_password = user.get("hashed_password") if user else None
    if not hashed_password or not verify_password(body.current_password, hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "현재 비밀번호가 올바르지 않습니다.")

    update_user_password(current_user.id, hash_password(body.new_password))
    return {"message": "비밀번호가 변경되었습니다."}
