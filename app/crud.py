from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application, User
from app.schemas import ApplicationCreate, UserCreate
from app.security import hash_password, verify_password


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


def get_applications(
    session: Session,
    owner_id: int,
    offset: int,
    limit: int,
    status: str | None = None,
    company: str | None = None,
    order_by: list | None = None,
) -> list[Application]:
    statement = (
        select(Application)
        .where(Application.owner_id == owner_id)
    )

    if status is not None:
        statement = statement.where(Application.status == status)

    if company is not None:
        statement = statement.where(
            Application.company.ilike(f"%{company}%")
        )

    if order_by is not None:
        statement = statement.order_by(*order_by)

    return list(
        session.scalars(
            statement.offset(offset).limit(limit)
        ).all()
    )


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
