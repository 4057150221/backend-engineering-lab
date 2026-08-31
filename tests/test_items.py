from fastapi.testclient import TestClient

from app.main import app, items

client = TestClient(app)


def setup_function() -> None:
    items.clear()


def test_create_item_with_all_fields():
    all_fields = {
        "title": "test_title",
        "description": "test_description",
    }
    response = client.post("/items", json=all_fields)
    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert response.json()["title"] == all_fields["title"]
    assert response.json()["description"] == all_fields["description"]


def test_create_item_with_title_only():
    title_only = {
        "title": "python",
    }
    response = client.post("/items", json=title_only)
    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert response.json()["title"] == title_only["title"]
    assert response.json()["description"] is None


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


def test_read_existing_item():
    all_fields = {
        "title": "test_title",
        "description": "test_description",
    }
    created_response = client.post("/items", json=all_fields)
    assert created_response.status_code == 201
    created_item = created_response.json()
    item_id = created_item["id"]

    read_response = client.get(f"/items/{item_id}")
    assert read_response.status_code == 200
    assert read_response.json() == created_item


def test_read_missing_item_returns_404():
    read_response = client.get("/items/999")
    assert read_response.status_code == 404
    assert read_response.json() == {"detail": "Item not found"}


def test_read_item_with_invalid_id():
    read_response = client.get("/items/invalid_id")
    assert read_response.status_code == 422


def test_read_items_with_offset_and_limit():
    payloads = [
        {
            "title": "first_title",
            "description": "first_description",
        },
        {
            "title": "second_title",
            "description": "second_description",
        },
        {
            "title": "third_title",
            "description": "third_description",
        },
    ]

    created_responses = [
        client.post("/items", json=payload)
        for payload in payloads
    ]

    for created_response in created_responses:
        assert created_response.status_code == 201


    list_response = client.get(
        "/items",
        params={
            "offset": 1,
            "limit": 1,
        },
    )

    expected_item = created_responses[1].json()

    assert list_response.status_code == 200
    assert isinstance(list_response.json(), list)
    assert len(list_response.json()) == 1
    assert list_response.json() == [expected_item]


def test_read_items_with_invalid_params():
    response = client.get(
        "/items",
        params={
            "offset": -1,
            "limit": 10,
        },
    )
    assert response.status_code == 422


def test_update_existing_item():
    all_fields = {
        "title": "test_title",
        "description": "test_description",
    }
    created_response = client.post("/items", json=all_fields)

    assert created_response.status_code == 201

    created_item = created_response.json()
    item_id = created_item["id"]


    update_payload = {
        "title": "New title",
        "description": "New description",
    }

    updated_response = client.put(f"/items/{item_id}", json=update_payload)

    expected_item = {
        "id": item_id,
        **update_payload,
    }

    assert updated_response.status_code == 200
    assert updated_response.json() == expected_item

    check_updated_response = client.get(f"/items/{item_id}")

    assert check_updated_response.status_code == 200
    assert check_updated_response.json() == expected_item


def test_update_missing_item_returns_404():
    update_payload = {
        "title": "New title",
        "description": "New description",
    }
    updated_response = client.put("/items/999", json=update_payload)
    assert updated_response.status_code == 404
    assert updated_response.json() == {"detail": "Item not found"}


def test_delete_existing_item():
    all_fields = {
        "title": "test_title",
        "description": "test_description",
    }
    created_response = client.post("/items", json=all_fields)

    assert created_response.status_code == 201

    created_item = created_response.json()
    item_id = created_item["id"]


    deleted_response = client.delete(f"/items/{item_id}")
    assert deleted_response.status_code == 204
    assert deleted_response.content == b""

    check_deleted_response = client.get(f"/items/{item_id}")
    assert check_deleted_response.status_code == 404


def test_delete_missing_item_returns_404():
    deleted_response = client.delete("/items/999")
    assert deleted_response.status_code == 404
    assert deleted_response.json() == {"detail": "Item not found"}