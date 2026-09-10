from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.models import User
from app.security import verify_password


client = TestClient(app)


def test_create_user_returns_public_user_data():
    user_data = {
        "email": "user@example.com",
        "password": "example-password",
    }

    response = client.post("/users", json=user_data)
    response_data = response.json()

    assert response.status_code == 201
    assert isinstance(response_data["id"], int)
    assert response_data["email"] == user_data["email"]
    assert "password" not in response_data
    assert "hashed_password" not in response_data


def test_create_user_stores_hashed_password(
    db_session: Session,
):
    user_data = {
        "email": "user@example.com",
        "password": "example-password",
    }

    response = client.post("/users", json=user_data)
    assert response.status_code == 201

    statement = select(User).where(User.email == user_data["email"])
    db_user = db_session.scalar(statement)

    assert db_user is not None
    assert db_user.hashed_password != user_data["password"]
    assert verify_password(
        user_data["password"],
        db_user.hashed_password,
    ) is True


def test_create_user_rejects_duplicate_email():
    user_data = {
        "email": "user@example.com",
        "password": "example-password",
    }

    first_response = client.post("/users", json=user_data)
    assert first_response.status_code == 201

    second_response = client.post("/users", json=user_data)
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Email already registered"
    }


def test_create_user_rejects_invalid_email():
    user_data = {
        "email": "not-an-email",
        "password": "example-password",
    }

    response = client.post("/users", json=user_data)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "email"]


def test_create_user_rejects_short_password():
    user_data = {
        "email": "user@example.com",
        "password": "short",
    }

    response = client.post("/users", json=user_data)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "password"]