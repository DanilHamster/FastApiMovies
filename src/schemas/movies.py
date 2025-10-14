from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class GenreBase(BaseModel):
    name: str


class GenreResponse(GenreBase):
    id: int

    class Config:
        from_attributes = True


class StarBase(BaseModel):
    name: str


class StarResponse(StarBase):
    id: int

    class Config:
        from_attributes = True


class DirectorBase(BaseModel):
    name: str


class DirectorResponse(DirectorBase):
    id: int

    class Config:
        from_attributes = True


class CertificationBase(BaseModel):
    name: str


class CertificationResponse(CertificationBase):
    id: int

    class Config:
        from_attributes = True


class MovieCreate(BaseModel):
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: str
    price: float
    certification_id: int
    genre_ids: list[int] = []
    star_ids: list[int] = []
    director_ids: list[int] = []


class MovieUpdate(BaseModel):
    name: Optional[str] = None
    year: Optional[int] = None
    time: Optional[int] = None
    imdb: Optional[float] = None
    votes: Optional[int] = None
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: Optional[str] = None
    price: Optional[float] = None
    certification_id: Optional[int] = None
    genre_ids: Optional[list[int]] = None
    star_ids: Optional[list[int]] = None
    director_ids: Optional[list[int]] = None


class MovieResponse(BaseModel):
    id: int
    uuid: UUID
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: Optional[float]
    gross: Optional[float]
    description: str
    price: float
    certification_id: int
    genres: list[GenreResponse] = []
    stars: list[StarResponse] = []
    directors: list[DirectorResponse] = []

    class Config:
        from_attributes = True
