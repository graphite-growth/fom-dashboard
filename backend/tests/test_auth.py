from datetime import datetime, timedelta, timezone

import jwt
import pytest
from starlette.testclient import TestClient

from app.auth import AUTH_SECRET, COOKIE_NAME, is_domain_allowed


def _make_token(
    email: str = "user@graphitehq.com",
    name: str = "Test User",
    expired: bool = False,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "123",
        "name": name,
        "email": email,
        "picture": "https://example.com/photo.jpg",
        "iat": now,
        "exp": now + timedelta(days=-1 if expired else 7),
    }
    return jwt.encode(payload, AUTH_SECRET, algorithm="HS256")


def test_me_unauthenticated(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_valid_token(client: TestClient) -> None:
    token = _make_token()
    client.cookies.set(COOKIE_NAME, token)
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "user@graphitehq.com"
    assert data["image"] == "https://example.com/photo.jpg"


def test_me_with_expired_token(client: TestClient) -> None:
    token = _make_token(expired=True)
    client.cookies.set(COOKIE_NAME, token)
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_invalid_token(client: TestClient) -> None:
    client.cookies.set(COOKIE_NAME, "garbage-token-value")
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_logout_clears_cookie(client: TestClient) -> None:
    response = client.get("/auth/logout", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/login"
    set_cookie = response.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie


def test_login_redirects_to_google(client: TestClient) -> None:
    response = client.get("/auth/login", follow_redirects=False)
    assert response.status_code == 302
    location = response.headers["location"]
    assert "accounts.google.com" in location


@pytest.mark.parametrize(
    "email, expected",
    [
        ("user@graphitehq.com", True),
        ("user@otherdomain.com", False),
        ("invalid-email", False),
    ],
)
def test_domain_restriction(email: str, expected: bool) -> None:
    assert is_domain_allowed(email) == expected
