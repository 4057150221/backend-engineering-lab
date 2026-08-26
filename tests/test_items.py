from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_item_with_all_fields():
    all_fields = {
        "title": "test_title",
        "description": "test_description",
    }
    response = client.post("/items", json=all_fields)
    assert response.status_code == 201
    assert response.json() == all_fields


def test_create_item_with_title_only():
    title_only = {
        "title": "python",
    }
    response = client.post("/items", json=title_only)
    assert response.status_code == 201
    assert response.json() == {
        "title": "python",
        "description": None,
    }


def test_create_item_without_title():
    without_title = {
        "description": "missing title",
    }
    response = client.post("/items", json=without_title)
    assert response.status_code == 422


def test_create_item_with_empty_title():
    with_empty_title = {
        "title": "",
    }
    response = client.post("/items", json=with_empty_title)
    assert response.status_code == 422