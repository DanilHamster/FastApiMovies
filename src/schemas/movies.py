from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from schemas import EmailRequestSchema


class GenreBase(BaseModel):
    name: str = Field(max_length=255)

    model_config = {"from_attributes": True}


class GenreResponse(GenreBase):
    id: int


class StarBase(BaseModel):
    name: str = Field(max_length=255)

    model_config = {"from_attributes": True}


class StarResponse(StarBase):
    id: int


class DirectorBase(BaseModel):
    name: str = Field(max_length=255)

    model_config = {"from_attributes": True}


class DirectorResponse(DirectorBase):
    id: int


class CertificationBase(BaseModel):
    name: str = Field(max_length=255)

    model_config = {"from_attributes": True}


class CertificationResponse(CertificationBase):
    id: int


class CommentBase(BaseModel):
    id: int


class CommentCreate(BaseModel):
    text: str


class Comment(CommentBase):
    text: str
    like_count: int = 0


Comment.model_rebuild()


class CommentResponse(BaseModel):
    id: int
    text: str
    like_count: int
    replies: List["Comment"] = []

    class Config:
        orm_mode = True


CommentResponse.model_rebuild()


class MovieBase(BaseModel):
    name: str = Field(max_length=255)
    year: int = Field(ge=1888, le=2100)
    time: int = Field(ge=1)
    imdb: float = Field(ge=0.0, le=10.0)
    votes: int = Field(ge=0)
    meta_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    gross: Optional[float] = Field(None, ge=0.0)
    description: str = Field(max_length=5000)
    price: float = Field(ge=0.0)
    certification_id: int = Field(ge=1)

    model_config = {"from_attributes": True}


class MovieCreate(MovieBase):
    genres: List[str] = Field(default_factory=list, min_length=0)
    stars: List[str] = Field(default_factory=list, min_length=0)
    directors: List[str] = Field(default_factory=list, min_length=0)


class MovieUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    year: Optional[int] = Field(None, ge=1888, le=2100)
    time: Optional[int] = Field(None, ge=1)
    imdb: Optional[float] = Field(None, ge=0.0, le=10.0)
    votes: Optional[int] = Field(None, ge=0)
    meta_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    gross: Optional[float] = Field(None, ge=0.0)
    description: Optional[str] = Field(None, max_length=5000)
    price: Optional[float] = Field(None, ge=0.0)
    certification_id: Optional[int] = Field(None, ge=1)
    genres: Optional[List[str]] = Field(default_factory=list, min_length=0)
    stars: Optional[List[str]] = Field(default_factory=list, min_length=0)
    directors: Optional[List[str]] = Field(default_factory=list, min_length=0)

    model_config = {"from_attributes": True}


class MovieDetail(MovieBase):
    id: int
    uuid: UUID
    genres: List[GenreResponse] = Field(default_factory=list)
    stars: List[StarResponse] = Field(default_factory=list)
    directors: List[DirectorResponse] = Field(default_factory=list)
    certification: CertificationResponse
    like_count: int = 0
    dislike_count: int = 0
    comments: List[CommentResponse]


class MovieList(BaseModel):
    id: int
    name: str
    year: int
    imdb: float
    price: float
    like_count: int = 0
    dislike_count: int = 0

    model_config = {"from_attributes": True}


class MovieListResponse(BaseModel):
    items: List[MovieList]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


class GenreBaseList(BaseModel):
    genre_name: str
    count: int
    link: str


class GenreResponseList(BaseModel):
    genres: List[GenreBaseList]
