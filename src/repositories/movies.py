from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models.movies import Movie
from database.models.genres import Genre
from database.models.stars import Star
from database.models.directors import Director
from database.models.certifications import Certification
from schemas.movies import MovieCreate, MovieUpdate


class MovieRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, model, **kwargs):
        stmt = select(model).filter_by(**kwargs)
        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance:
            return instance
        new_instance = model(**kwargs)
        self.session.add(new_instance)
        await self.session.flush()
        return new_instance

    async def create(self, movie_data: MovieCreate) -> Movie:
        certification = await self.get_or_create(Certification, id=movie_data.certification_id)
        genre_objs = [await self.get_or_create(Genre, id=gid) for gid in movie_data.genre_ids]
        star_objs = [await self.get_or_create(Star, id=sid) for sid in movie_data.star_ids]
        director_objs = [await self.get_or_create(Director, id=did) for did in movie_data.director_ids]

        movie = Movie(
            **movie_data.model_dump(exclude={"genre_ids", "star_ids", "director_ids"}),
            certification=certification,
            genres=genre_objs,
            stars=star_objs,
            directors=director_objs
        )
        self.session.add(movie)
        await self.session.commit()
        await self.session.refresh(movie)
        return movie

    async def get_by_id(self, movie_id: int) -> Movie | None:
        result = await self.session.execute(
            select(Movie)
            .options(
                joinedload(Movie.certification),
                joinedload(Movie.genres),
                joinedload(Movie.stars),
                joinedload(Movie.directors),
            )
            .where(Movie.id == movie_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Movie]:
        result = await self.session.execute(
            select(Movie)
            .offset(skip)
            .limit(limit)
            .order_by(Movie.id.desc())
            .options(
                joinedload(Movie.certification),
                joinedload(Movie.genres),
                joinedload(Movie.stars),
                joinedload(Movie.directors),
            )
        )
        return result.scalars().all()

    async def update(self, movie_id: int, movie_data: MovieUpdate) -> Movie | None:
        movie = await self.get_by_id(movie_id)
        if not movie:
            return None

        update_data = movie_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(movie, key, value)

        await self.session.commit()
        await self.session.refresh(movie)
        return movie

    async def delete(self, movie_id: int) -> bool:
        movie = await self.get_by_id(movie_id)
        if not movie:
            return False

        await self.session.delete(movie)
        await self.session.commit()
        return True
