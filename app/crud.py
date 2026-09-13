from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Item, User
from app.schemas import ItemCreate, UserCreate
from app.security import hash_password, verify_password


def create_item(
    session: Session,
    item_data: ItemCreate,
) -> Item:
    db_item = Item(
        title=item_data.title,
        description=item_data.description,
    )

    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def get_item(
    session: Session,
    item_id: int,
) -> Item | None:
    return session.get(Item, item_id)


def get_items(
    session: Session,
    offset: int,
    limit: int,
) -> list[Item]:
    statement = (
        select(Item)
        .order_by(Item.id)
        .offset(offset)
        .limit(limit)
    )

    return list(session.scalars(statement).all())


def update_item(
    session: Session,
    db_item: Item,
    item_data: ItemCreate,
) -> Item:
    db_item.title = item_data.title
    db_item.description = item_data.description

    session.commit()
    session.refresh(db_item)

    return db_item


def delete_item(
    session: Session,
    db_item: Item,
) -> None:
    session.delete(db_item)
    session.commit()


def get_user_by_email(
    session: Session,
    email: str,
) -> User | None:
    statement = select(User).where(User.email == email)
    return session.scalar(statement)


def create_user(
    session: Session,
    user_data: UserCreate,
) -> User:
    db_user = User(
        email=str(user_data.email),
        hashed_password=hash_password(user_data.password),
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


def authenticate_user(
    session: Session,
    email: str,
    plain_password: str,
) -> User | None:
    user = get_user_by_email(session, email)

    if user is None:
        return None

    if not verify_password(plain_password, user.hashed_password):
        return None

    return user
