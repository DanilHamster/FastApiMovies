from typing import Any, List, Tuple, Type

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models.movies import (
    DirectorModel,
    GenreModel,
    MovieModel,
    StarModel,
)
from filters.filter_movies import MovieFilter
from schemas.movies import MovieCreate, MovieUpdate


class MovieRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, model: Type[Any], **kwargs: Any) -> Any:
        stmt = select(model).filter_by(**kwargs)
        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance:
            return instance
        new_instance = model(**kwargs)
        self.session.add(new_instance)
        await self.session.flush()
        return new_instance

    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> Tuple[List[MovieModel], int]:
        count_result = await self.session.execute(
            select(func.count()).select_from(MovieModel)
        )
        total_count = count_result.scalar() or 0

        result = await self.session.execute(
            select(MovieModel)
            .offset(skip)
            .limit(limit)
            .order_by(MovieModel.id.desc())
            .options(
                joinedload(MovieModel.certification),
                joinedload(MovieModel.genres),
                joinedload(MovieModel.stars),
                joinedload(MovieModel.directors),
            )
        )
        movies = list(result.unique().scalars().all())
        return movies, total_count

    async def get_by_id(self, movie_id: int) -> MovieModel | None:
        result = await self.session.execute(
            select(MovieModel)
            .options(
                joinedload(MovieModel.certification),
                joinedload(MovieModel.genres),
                joinedload(MovieModel.stars),
                joinedload(MovieModel.directors),
            )
            .where(MovieModel.id == movie_id)
        )
        return result.unique().scalar_one_or_none()

    async def create(self, movie_data: MovieCreate) -> MovieModel:
        movie_to_search = await self.session.execute(
            select(MovieModel).where(
                MovieModel.name == movie_data.name,
                MovieModel.year == movie_data.year,
                MovieModel.time == movie_data.time,
            )
        )
        movie = movie_to_search.scalar_one_or_none()
        if movie:
            raise HTTPException(
                status_code=409, detail="Such a movie already exists"
            )

        genre_objs = [
            await self.get_or_create(GenreModel, name=g)
            for g in movie_data.genres
        ]
        star_objs = [
            await self.get_or_create(StarModel, name=s)
            for s in movie_data.stars
        ]
        director_objs = [
            await self.get_or_create(DirectorModel, name=d)
            for d in movie_data.directors
        ]

        new_movie = MovieModel(
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
        return await self.get_by_id(new_movie.id)

    async def update(
        self, movie_id: int, movie_data: MovieUpdate
    ) -> MovieModel | None:
        movie = await self.get_by_id(movie_id)
        if not movie:
            return None

        update_dict = movie_data.model_dump(exclude_unset=True)

        if "genres" in update_dict:
            genre_names = update_dict.pop("genres")
            movie.genres = [
                await self.get_or_create(GenreModel, name=g)
                for g in genre_names
            ]

        if "stars" in update_dict:
            star_names = update_dict.pop("stars")
            movie.stars = [
                await self.get_or_create(StarModel, name=s) for s in star_names
            ]

        if "directors" in update_dict:
            director_names = update_dict.pop("directors")
            movie.directors = [
                await self.get_or_create(DirectorModel, name=d)
                for d in director_names
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

    async def filter_movies(
        self, filters: MovieFilter, skip: int = 0, limit: int = 10
    ) -> Tuple[List[MovieModel], int]:
        query = select(MovieModel).distinct()
        query = query.outerjoin(MovieModel.directors).outerjoin(
            MovieModel.stars
        )
        search_conditions = []
        if filters.name__ilike:
            search_conditions.append(
                MovieModel.name.ilike(f"%{filters.name__ilike}%")
            )
        if filters.description__ilike:
            search_conditions.append(
                MovieModel.description.ilike(f"%{filters.description__ilike}%")
            )
        if filters.director_name__ilike:
            search_conditions.append(
                DirectorModel.name.ilike(f"%{filters.director_name__ilike}%")
            )
        if filters.star_name__ilike:
            search_conditions.append(
                StarModel.name.ilike(f"%{filters.star_name__ilike}%")
            )

        if search_conditions:
            query = query.filter(or_(*search_conditions))
        if filters.year__gte is not None:
            query = query.filter(MovieModel.year >= filters.year__gte)
        if filters.year__lte is not None:
            query = query.filter(MovieModel.year <= filters.year__lte)
        if filters.imdb__gte is not None:
            query = query.filter(MovieModel.imdb >= filters.imdb__gte)
        if filters.imdb__lte is not None:
            query = query.filter(MovieModel.imdb <= filters.imdb__lte)
        if filters.price__gte is not None:
            query = query.filter(MovieModel.price >= filters.price__gte)
        if filters.price__lte is not None:
            query = query.filter(MovieModel.price <= filters.price__lte)
        if filters.certification_id is not None:
            query = query.filter(
                MovieModel.certification_id == filters.certification_id
            )
        if filters.genre_id is not None:
            query = query.filter(MovieModel.genres.any(id=filters.genre_id))
        if filters.order_by:
            query = filters.sort(query)
        count_query = select(func.count(MovieModel.id)).select_from(
            query.subquery()
        )
        total_count = await self.session.scalar(count_query)
        query = (
            query.options(
                joinedload(MovieModel.certification),
                joinedload(MovieModel.genres),
                joinedload(MovieModel.stars),
                joinedload(MovieModel.directors),
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        movies = list(result.unique().scalars().all())
        total_count = total_count or 0

        return movies, total_count
