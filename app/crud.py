from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application, Item, User
from app.schemas import ApplicationCreate, ItemCreate, UserCreate
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


def create_application(
    session: Session,
    application_data: ApplicationCreate,
    owner_id: int,
) -> Application:
    db_application = Application(
        company=application_data.company,
        position=application_data.position,
        status=application_data.status.value,
        applied_at=application_data.applied_at,
        notes=application_data.notes,
        owner_id=owner_id,
    )

    session.add(db_application)
    session.commit()
    session.refresh(db_application)
    return db_application


# TODO(user): get_application(session, application_id, owner_id) -> Application | None
#   必须在同一个 WHERE 里同时过滤 id 和 owner_id，不要先查到再在 Python 里比较 owner。
def get_application(
    session: Session,
    application_id: int,
    owner_id: int,
) -> Application | None:
    statement = select(Application).where(
        Application.id == application_id,
        Application.owner_id == owner_id,
    )

    return session.scalar(statement)


# TODO(user): get_applications(session, owner_id, offset, limit) -> list[Application]
#   在 get_items 的 offset/limit 基础上加 owner_id 过滤条件。
def get_applications(
    session: Session,
    owner_id: int,
    offset: int,
    limit: int,
) -> list[Application]:
    statement = (
        select(Application)
        .where(Application.owner_id == owner_id)
        .order_by(Application.id)
        .offset(offset)
        .limit(limit)
    )

    return list(session.scalars(statement).all())


def update_application(
    session: Session,
    db_application: Application,
    application_data: ApplicationCreate,
) -> Application:
    db_application.company = application_data.company
    db_application.position = application_data.position
    db_application.status = application_data.status.value
    db_application.applied_at = application_data.applied_at
    db_application.notes = application_data.notes

    session.commit()
    session.refresh(db_application)

    return db_application


def delete_application(
    session: Session,
    db_application: Application,
) -> None:
    session.delete(db_application)
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
