"""보안 보강 동작 확인.

- SECRET_KEY가 기본값이면 기동 검사가 막는다.
- 로그인은 5번 연속 실패하면 잠기고, 성공하면 실패 횟수가 초기화된다.
- 비밀번호는 8자 이상이어야 한다.

무거운 분석 모듈을 불러오지 않도록 auth 라우터만 작은 앱에 붙여서 돌린다.
"""
import bcrypt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import security
from app.routers import auth as auth_router


def test_secret_key_default_is_rejected():
    with pytest.raises(RuntimeError):
        security.check_secret_key("change-me-in-production")
    with pytest.raises(RuntimeError):
        security.check_secret_key("")
    # 32자 이상 임의 값은 통과한다.
    security.check_secret_key("x" * 40)


@pytest.fixture
def client(monkeypatch):
    hashed = bcrypt.hashpw(b"correct-pw", bcrypt.gensalt()).decode()
    user = {"id": "u1", "email": "a@b.com", "hashed_password": hashed, "name": None}
    monkeypatch.setattr(auth_router, "get_user_by_email", lambda email: user if email == "a@b.com" else None)
    monkeypatch.setattr(auth_router, "create_user", lambda email, pw, name: {"id": "u2", "email": email})
    auth_router._login_fails.clear()

    app = FastAPI()
    app.include_router(auth_router.router, prefix="/api/auth")
    return TestClient(app)


def _login(client, password):
    return client.post("/api/auth/login", json={"email": "a@b.com", "password": password})


def test_login_locks_after_five_failures(client):
    for _ in range(5):
        assert _login(client, "wrong").status_code == 401
    # 잠긴 동안에는 맞는 비밀번호여도 429
    res = _login(client, "correct-pw")
    assert res.status_code == 429
    assert "분 후" in res.json()["detail"]


def test_login_success_resets_failures(client):
    for _ in range(4):
        assert _login(client, "wrong").status_code == 401
    assert _login(client, "correct-pw").status_code == 200
    # 성공 뒤에는 다시 4번 틀려도 잠기지 않는다.
    for _ in range(4):
        assert _login(client, "wrong").status_code == 401
    assert _login(client, "correct-pw").status_code == 200


def test_signup_requires_8_chars(client):
    res = client.post("/api/auth/signup", json={"email": "new@b.com", "password": "1234567"})
    assert res.status_code == 422
    res = client.post("/api/auth/signup", json={"email": "new@b.com", "password": "12345678"})
    assert res.status_code == 201
