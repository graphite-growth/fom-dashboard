import pytest
from starlette.testclient import TestClient


@pytest.fixture(autouse=True)
def _env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test")
    monkeypatch.setenv("AUTH_URL", "http://localhost:3000")
    monkeypatch.setenv("AUTH_SECRET", "test-secret-key-for-jwt")
    monkeypatch.setenv("ALLOWED_DOMAIN", "graphitehq.com")


@pytest.fixture()
def client() -> TestClient:
    from main import app

    return TestClient(app)
