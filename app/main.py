from fastapi import FastAPI
from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=300)


app = FastAPI()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/items", status_code=201)
async def create_item(item: ItemCreate) -> ItemCreate:
    return item