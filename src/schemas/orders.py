from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrderItemOutSchema(BaseModel):
    movie_id: int = Field(description="ID of the movie")
    price_at_order: str = Field(
        description="Price captured at the time of ordering"
    )


class OrderOutSchema(BaseModel):
    id: int
    status: str
    total_amount: str
    created_at: datetime | None = None
    items: list[OrderItemOutSchema]


class OrderItemMovieSchema(BaseModel):
    id: int
    name: str


class OrderItemDetailOutSchema(BaseModel):
    movie: OrderItemMovieSchema
    price_at_order: str


class OrderDetailOutSchema(BaseModel):
    id: int
    status: str
    total_amount: str
    created_at: datetime | None = None
    items: list[OrderItemDetailOutSchema]
