from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Item
from app.schemas import ItemCreate


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