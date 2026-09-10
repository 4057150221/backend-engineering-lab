from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud
from app.database import get_session
from app.models import Item, User
from app.schemas import ItemCreate, ItemRead, UserCreate, UserRead


def _get_item_or_404(
    session: Session,
    item_id: int,
) -> Item:
    db_item = crud.get_item(
        session=session,
        item_id=item_id,
    )

    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    return db_item


app = FastAPI()


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
    "/items",
    response_model=ItemRead,
    status_code=201,
)
def create_item(
    item_data: ItemCreate,
    session: Session = Depends(get_session),
) -> Item:
    return crud.create_item(
        session=session,
        item_data=item_data,
    )


@app.get(
    "/items/{item_id}",
    response_model=ItemRead,
)
def read_item(
    item_id: int,
    session: Session = Depends(get_session),
) -> Item:
    return _get_item_or_404(
        session=session,
        item_id=item_id,
    )


@app.get(
    "/items",
    response_model=list[ItemRead],
)
def read_items(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[Item]:
    return crud.get_items(
        session=session,
        offset=offset,
        limit=limit,
    )


@app.put(
    "/items/{item_id}",
    response_model=ItemRead,
)
def update_item(
    item_id: int,
    item_data: ItemCreate,
    session: Session = Depends(get_session),
) -> Item:
    db_item = _get_item_or_404(
        session=session,
        item_id=item_id,
    )

    return crud.update_item(
        session=session,
        db_item=db_item,
        item_data=item_data,
    )


@app.delete(
    "/items/{item_id}",
    status_code=204,
)
def delete_item(
    item_id: int,
    session: Session = Depends(get_session),
) -> None:
    db_item = _get_item_or_404(
        session=session,
        item_id=item_id,
    )

    crud.delete_item(
        session=session,
        db_item=db_item,
    )