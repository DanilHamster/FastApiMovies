from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter

from database.models.movies import MovieModel

class MovieFilter(Filter):
    name__ilike: Optional[str] = None
    description__ilike: Optional[str] = None
    year__gte: Optional[int] = None
    year__lte: Optional[int] = None
    imdb__gte: Optional[float] = None
    imdb__lte: Optional[float] = None
    price__gte: Optional[float] = None
    price__lte: Optional[float] = None
    certification_id: Optional[int] = None
    genre_id: Optional[int] = None
    director_name__ilike: Optional[str] = None
    star_name__ilike: Optional[str] = None
    order_by: Optional[str] = None

    class Constants(Filter.Constants):
        model = MovieModel
