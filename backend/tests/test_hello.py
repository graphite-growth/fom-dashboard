from starlette.testclient import TestClient


def test_get_hello(client: TestClient) -> None:
    response = client.get("/hello")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Hello, world!!!"
    assert data["method"] == "GET"


def test_put_hello(client: TestClient) -> None:
    response = client.put("/hello")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Hello, world!"
    assert data["method"] == "PUT"


def test_get_hello_name(client: TestClient) -> None:
    response = client.get("/hello/Alice")
    assert response.status_code == 200
    assert response.json()["message"] == "Hello, Alice!"


def test_get_hello_name_url_encoded(client: TestClient) -> None:
    response = client.get("/hello/John%20Doe")
    assert response.status_code == 200
    assert response.json()["message"] == "Hello, John Doe!"
