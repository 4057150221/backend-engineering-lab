from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.main import app
from app.models import Item, User


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(bind=test_engine)

Base.metadata.create_all(test_engine)


def override_get_session() -> Generator[Session, None, None]:
    with TestSessionLocal() as session:
        yield session


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(autouse=True)
def clean_database() -> None:
    with TestSessionLocal.begin() as session:
        session.execute(delete(Item))
        session.execute(delete(User))
