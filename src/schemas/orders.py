from datetime import datetime

from pydantic import BaseModel, Field


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

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 123,
                "status": "pending",
                "total_amount": "29.98",
                "created_at": "2025-01-01T12:00:00+00:00",
                "items": [
                    {"movie_id": 1, "price_at_order": "14.99"},
                    {"movie_id": 2, "price_at_order": "14.99"},
                ],
            }
        }
    }


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

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 321,
                "status": "paid",
                "total_amount": "19.99",
                "created_at": "2025-01-02T09:15:00+00:00",
                "items": [
                    {
                        "movie": {"id": 10, "name": "Inception"},
                        "price_at_order": "19.99",
                    }
                ],
            }
        }
    }
