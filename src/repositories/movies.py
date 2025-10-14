from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.movies import Movie
from schemas.movies import MovieCreate, MovieUpdate


class MovieRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, movie_data: MovieCreate) -> Movie:
        movie = Movie(**movie_data.model_dump())
        self.session.add(movie)
        await self.session.commit()
        await self.session.refresh(movie)
        return movie

    async def get_by_id(self, movie_id: int) -> Movie | None:
        query = select(Movie).where(Movie.id == movie_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Movie]:
        query = select(Movie).offset(skip).limit(limit)
        result = await self.session.execute(query)
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
