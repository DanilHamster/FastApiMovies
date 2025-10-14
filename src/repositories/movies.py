from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from database.models.movies import Movie
from database.models.genres import Genre
from database.models.stars import Star
from database.models.directors import Director
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

    async def get_all(self, skip: int = 0, limit: int = 100) -> tuple[list[Movie], int]:
        count_result = await self.session.execute(
            select(func.count()).select_from(Movie)
        )
        total_count = count_result.scalar()

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
        movies = result.scalars().all()
        return movies, total_count

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

    async def create(self, movie_data: MovieCreate) -> Movie:
        genre_objs = [
            await self.get_or_create(Genre, id=genre_id)
            for genre_id in movie_data.genre_ids
        ]
        star_objs = [
            await self.get_or_create(Star, id=star_id)
            for star_id in movie_data.star_ids
        ]
        director_objs = [
            await self.get_or_create(Director, id=director_id)
            for director_id in movie_data.director_ids
        ]

        new_movie = Movie(
            name=movie_data.name,
            year=movie_data.year,
            time=movie_data.time,
            imdb=movie_data.imdb,
            votes=movie_data.votes,
            meta_score=movie_data.meta_score,
            gross=movie_data.gross,
            description=movie_data.description,
            price=movie_data.price,
            certification_id=movie_data.certification_id,
            genres=genre_objs,
            stars=star_objs,
            directors=director_objs,
        )
        self.session.add(new_movie)
        await self.session.commit()
        await self.session.refresh(new_movie)

        full_movie = await self.get_by_id(new_movie.id)
        return full_movie

    async def update(self, movie_id: int, movie_data: MovieUpdate) -> Movie | None:
        movie = await self.get_by_id(movie_id)
        if not movie:
            return None

        update_dict = movie_data.model_dump(exclude_unset=True)

        if "genre_ids" in update_dict:
            genre_ids = update_dict.pop("genre_ids")
            movie.genres = [
                await self.get_or_create(Genre, id=genre_id)
                for genre_id in genre_ids
            ]

        if "star_ids" in update_dict:
            star_ids = update_dict.pop("star_ids")
            movie.stars = [
                await self.get_or_create(Star, id=star_id)
                for star_id in star_ids
            ]

        if "director_ids" in update_dict:
            director_ids = update_dict.pop("director_ids")
            movie.directors = [
                await self.get_or_create(Director, id=director_id)
                for director_id in director_ids
            ]

        for key, value in update_dict.items():
            setattr(movie, key, value)

        await self.session.commit()
        await self.session.refresh(movie)
        return await self.get_by_id(movie.id)

    async def delete(self, movie_id: int) -> bool:
        movie = await self.get_by_id(movie_id)
        if not movie:
            return False

        await self.session.delete(movie)
        await self.session.commit()
        return True
