from typing import Any, List, Tuple, Type

from fastapi import BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from config import get_accounts_email_notificator
from database import UserModel
from database.models.movies import Comment, DirectorModel, GenreModel, MovieModel, StarModel
from notifications import EmailSenderInterface
from schemas.movies import MovieCreate, MovieDetail, MovieUpdate


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

    async def get_all(self, skip: int = 0, limit: int = 100) -> Tuple[List[MovieModel], int]:
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
                selectinload(MovieModel.comments).selectinload(Comment.replies).selectinload(Comment.replies)
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
                status_code=409,
                detail="Such a movie already exists",
            )

        genre_objs = [
            await self.get_or_create(GenreModel, name=genre_name)
            for genre_name in movie_data.genres
        ]
        star_objs = [
            await self.get_or_create(StarModel, name=star_name)
            for star_name in movie_data.stars
        ]
        director_objs = [
            await self.get_or_create(DirectorModel, name=director_name)
            for director_name in movie_data.directors
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

        full_movie = await self.get_by_id(new_movie.id)
        return full_movie

    async def update(self, movie_id: int, movie_data: MovieUpdate) -> MovieModel | None:
        movie = await self.get_by_id(movie_id)

        if not movie:
            return None

        update_dict = movie_data.model_dump(exclude_unset=True)

        if "genres" in update_dict:
            genre_ids = update_dict.pop("genres")
            movie.genres = [
                await self.get_or_create(GenreModel, name=genre_name)
                for genre_name in genre_ids
            ]

        if "stars" in update_dict:
            star_ids = update_dict.pop("stars")
            movie.stars = [
                await self.get_or_create(StarModel, name=star_name)
                for star_name in star_ids
            ]

        if "directors" in update_dict:
            director_ids = update_dict.pop("directors")
            movie.directors = [
                await self.get_or_create(DirectorModel, name=director_name)
                for director_name in director_ids
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


async def notify_comment_like_user(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    target_id: int,
    email_sender: EmailSenderInterface
) -> None:

    comment = await db.execute(select(Comment).where(Comment.id == target_id))
    comment_db = comment.scalar_one_or_none()

    if comment_db is None:
        return

    user = await db.execute(select(UserModel).where(UserModel.id == comment_db.user_id))
    db_user = user.scalar_one_or_none()

    if db_user is None:
        return

    background_tasks.add_task(
        email_sender.send_comments_notify_like,
        str(db_user.email)
    )
