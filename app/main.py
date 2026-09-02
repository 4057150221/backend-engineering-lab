from fastapi import FastAPI, HTTPException, Query

from app.schemas import ItemCreate, ItemRead


items: dict[int, ItemRead] = {}


def _get_item_or_404(item_id: int) -> ItemRead:
    item = items.get(item_id)

    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    return item


app = FastAPI()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/items", status_code=201)
async def create_item(item: ItemCreate) -> ItemRead:
    new_id = max(items.keys(), default=0) + 1
    created_item = ItemRead(
        id=new_id,
        title=item.title,
        description=item.description,
    )
    items[new_id] = created_item
    return created_item


@app.get("/items/{item_id}")
async def read_item(item_id: int) -> ItemRead:
    return _get_item_or_404(item_id)


@app.get("/items")
async def read_items(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
) -> list[ItemRead]:
    all_items = list(items.values())
    return all_items[offset : offset + limit]


@app.put("/items/{item_id}")
async def update_item(
    item_id: int,
    item: ItemCreate,
) -> ItemRead:
    _get_item_or_404(item_id)
    updated_item = ItemRead(
        id=item_id,
        title=item.title,
        description=item.description,
    )
    items[item_id] = updated_item
    return updated_item


@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int) -> None:
    _get_item_or_404(item_id)
    del items[item_id]