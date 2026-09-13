from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud
from app.main import app
from app.models import User
from app.schemas import UserCreate
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


def test_authenticate_user_returns_user_for_correct_credentials(
    db_session: Session,
):
    email = "user@example.com"
    plain_password = "correct-password-for-test"

    user_data = UserCreate(
        email=email,
        password=plain_password,
    )

    created_user = crud.create_user(db_session, user_data)
    authenticated_user = crud.authenticate_user(
        session=db_session,
        email=email,
        plain_password=plain_password,
    )

    assert authenticated_user is not None
    assert authenticated_user.id == created_user.id
    assert authenticated_user.email == email


def test_authenticate_user_returns_none_for_incorrect_password(
    db_session: Session,
):
    email = "user@example.com"
    plain_password = "correct-password-for-test"
    wrong_password = "wrong-password-for-test"

    user_data = UserCreate(
        email=email,
        password=plain_password,
    )

    crud.create_user(db_session, user_data)
    authenticated_user = crud.authenticate_user(
        session=db_session,
        email=email,
        plain_password=wrong_password,
    )

    assert authenticated_user is None


def test_authenticate_user_returns_none_for_unknown_email(
    db_session: Session,
):
    authenticated_user = crud.authenticate_user(
        session=db_session,
        email="missing@example.com",
        plain_password="example-password",
    )

    assert authenticated_user is None


def test_login_returns_bearer_access_token():
    user_data = {
        "email": "user@example.com",
        "password": "example-password",
    }

    register_response = client.post("/users", json=user_data)
    assert register_response.status_code == 201

    login_data = {
        "username": user_data["email"],
        "password": user_data["password"],
    }

    login_response = client.post("/token", data=login_data)
    login_response_data = login_response.json()

    assert login_response.status_code == 200
    assert login_response_data["token_type"] == "bearer"
    assert isinstance(login_response_data["access_token"], str)
    assert login_response_data["access_token"].count(".") == 2


def test_login_rejects_incorrect_password():
    user_data = {
        "email": "user@example.com",
        "password": "example-password",
    }

    register_response = client.post("/users", json=user_data)
    assert register_response.status_code == 201

    wrong_password = "example-wrong-password"
    wrong_login_data = {
        "username": user_data["email"],
        "password": wrong_password,
    }

    login_response = client.post("/token", data=wrong_login_data)
    login_response_data = login_response.json()

    assert login_response.status_code == 401
    assert login_response_data == {"detail": "Incorrect email or password"}
    assert login_response.headers["www-authenticate"] == "Bearer"


def test_login_rejects_unknown_email():
    login_data = {
        "username": "missing@example.com",
        "password": "example-password",
    }

    login_response = client.post("/token", data=login_data)

    assert login_response.status_code == 401
    assert login_response.json() == {"detail": "Incorrect email or password"}
    assert login_response.headers["www-authenticate"] == "Bearer"


def test_read_current_user_returns_authenticated_user():
    user_data = {
        "email": "user@example.com",
        "password": "example-password",
    }

    register_response = client.post("/users", json=user_data)
    assert register_response.status_code == 201
    registered_user = register_response.json()

    login_data = {
        "username": user_data["email"],
        "password": user_data["password"],
    }

    login_response = client.post("/token", data=login_data)
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    current_user_response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )
    current_user_data = current_user_response.json()

    assert current_user_response.status_code == 200
    assert current_user_data["id"] == registered_user["id"]
    assert current_user_data["email"] == registered_user["email"]
    assert "password" not in current_user_data
    assert "hashed_password" not in current_user_data


def test_read_current_user_rejects_missing_authorization_header():
    response = client.get("/users/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_read_current_user_rejects_invalid_token():
    headers = {
        "Authorization": "Bearer not-a-valid-jwt",
    }
    response = client.get("/users/me", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_read_current_user_rejects_token_for_deleted_user(
    db_session: Session,
):
    user_data = {
        "email": "user@example.com",
        "password": "example-password",
    }

    register_response = client.post("/users", json=user_data)
    assert register_response.status_code == 201
    registered_user = register_response.json()

    login_data = {
        "username": user_data["email"],
        "password": user_data["password"],
    }

    login_response = client.post("/token", data=login_data)
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    db_user = db_session.get(User, registered_user["id"])
    assert db_user is not None

    db_session.delete(db_user)
    db_session.commit()

    response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}
    assert response.headers["www-authenticate"] == "Bearer"