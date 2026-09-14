from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app import crud
from app.database import get_session
from app.models import Application, User
from app.schemas import (
    ApplicationCreate,
    ApplicationRead,
    Token,
    UserCreate,
    UserRead,
)
from app.security import create_access_token, decode_access_token


def _get_application_or_404(
    session: Session,
    application_id: int,
    owner_id: int,
) -> Application:
    db_application = crud.get_application(
        session=session,
        application_id=application_id,
        owner_id=owner_id,
    )

    if db_application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    return db_application


app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/users",
    response_model=UserRead,
    status_code=201,
)
def create_user(
    user_data: UserCreate,
    session: Session = Depends(get_session),
) -> User:
    existing_user = crud.get_user_by_email(
        session=session,
        email=str(user_data.email),
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    return crud.create_user(
        session=session,
        user_data=user_data,
    )


@app.post(
    "/token",
    response_model=Token,
)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> Token:
    email = form_data.username
    plain_password = form_data.password

    user = crud.authenticate_user(
        session=session,
        email=email,
        plain_password=plain_password,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)
    return Token(access_token=access_token, token_type="bearer")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        sub = decode_access_token(token)
        user_id = int(sub)
    except (InvalidTokenError, ValueError):
        raise credentials_exception

    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user


@app.get(
    "/users/me",
    response_model=UserRead,
)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


@app.post(
    "/applications",
    response_model=ApplicationRead,
    status_code=201,
)
def create_application(
    application_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Application:
    return crud.create_application(
        session=session,
        application_data=application_data,
        owner_id=current_user.id,
    )


@app.get(
    "/applications/{application_id}",
    response_model=ApplicationRead,
)
def read_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Application:
    return _get_application_or_404(
        session=session,
        application_id=application_id,
        owner_id=current_user.id,
    )


@app.get(
    "/applications",
    response_model=list[ApplicationRead],
)
def read_applications(
    current_user: User = Depends(get_current_user),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[Application]:
    return crud.get_applications(
        session=session,
        owner_id=current_user.id,
        offset=offset,
        limit=limit,
    )


@app.put(
    "/applications/{application_id}",
    response_model=ApplicationRead,
)
def update_application(
    application_id: int,
    application_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Application:
    db_application = _get_application_or_404(
        session=session,
        application_id=application_id,
        owner_id=current_user.id,
    )

    return crud.update_application(
        session=session,
        db_application=db_application,
        application_data=application_data,
    )


@app.delete(
    "/applications/{application_id}",
    status_code=204,
)
def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    db_application = _get_application_or_404(
        session=session,
        application_id=application_id,
        owner_id=current_user.id,
    )

    crud.delete_application(
        session=session,
        db_application=db_application,
    )
