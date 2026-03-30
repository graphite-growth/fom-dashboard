import pytest
from starlette.testclient import TestClient

from app.auth import COOKIE_NAME, create_token


@pytest.fixture()
def dev_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Client with DEV_AUTH enabled — reimports main so the middleware registers."""
    monkeypatch.setenv("DEV_AUTH", "true")

    import importlib

    import main

    importlib.reload(main)
    return TestClient(main.app, follow_redirects=False)


def test_no_redirect_without_dev_auth(client: TestClient) -> None:
    """Without DEV_AUTH the middleware is absent; unauthenticated requests pass through."""
    response = client.get("/auth/me")
    # No redirect — just the normal 401 from the route guard
    assert response.status_code == 401


def test_redirect_sets_cookie_with_dev_auth(dev_client: TestClient) -> None:
    """With DEV_AUTH, a request without a session cookie gets a redirect + cookie."""
    response = dev_client.get("/hello")
    assert response.status_code == 307
    assert COOKIE_NAME in response.cookies
    # Redirects to AUTH_URL so the cookie works behind a reverse proxy
    assert response.headers["location"] == "http://localhost:3000"


def test_passthrough_when_cookie_present(dev_client: TestClient) -> None:
    """With DEV_AUTH, a request that already carries the cookie is served normally."""
    token = create_token(
        {
            "sub": "dev",
            "name": "Dev User",
            "email": "dev@example.com",
            "picture": "",
        }
    )
    dev_client.cookies.set(COOKIE_NAME, token)
    response = dev_client.get("/hello")
    assert response.status_code == 200
