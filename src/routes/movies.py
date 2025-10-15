from math import ceil
from typing import Any, List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
)
from sqlalchemy import select, func
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from fastapi_filter import FilterDepends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_accounts_email_notificator
from database import MovieModel, UserModel, get_db
from database.models.movies import (
    Comment,
    DislikeModel,
    LikeModel,
    LikeTargetType,
    GenreModel,
)
from notifications import EmailSenderInterface
from repositories.movies import MovieRepository, notify_comment_like_user
from schemas.movies import (
    CommentCreate,
    CommentResponse,
    MovieCreate,
    MovieDetail,
    MovieListResponse,
    MovieUpdate,
    GenreResponseList,
    GenreBase,
)
from database import get_db
from filters.filter_movies import MovieFilter
from repositories.movies import MovieRepository
from schemas.movies import (
    MovieCreate,
    MovieDetail,
    MovieListResponse,
    MovieUpdate,
)
from utils import get_current_user
from schemas.movies import (
    MovieCreate,
    MovieDetail,
    MovieListResponse,
    MovieUpdate,
)

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get(
    "/",
    response_model=MovieListResponse,
    summary="Get filtered and paginated list of movies",
    description=(
        "<h3>Retrieve a paginated list of movies with filters and sorting.</h3>"
        "<ul>"
        "<li><code>?year__gte=2010&imdb__lte=9</code></li>"
        "<li><code>?genre_id=2&order_by=-imdb</code></li>"
        "<li><code>?name__ilike=Matrix</code></li>"
        "</ul>"
    ),
    responses={
        200: {"description": "Movies retrieved successfully."},
        404: {
            "description": "No movies found.",
            "content": {
                "application/json": {"example": {"detail": "No movies found"}}
            },
        },
    },
)
async def list_movies(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(
        10, ge=1, le=100, description="Movies per page (1–100)"
    ),
    filters: MovieFilter = FilterDepends(MovieFilter),
    session: AsyncSession = Depends(get_db),
) -> MovieListResponse:
    repo = MovieRepository(session)
    skip = (page - 1) * per_page

    movies, total_count = await repo.filter_movies(
        filters=filters, skip=skip, limit=per_page
    )

    if total_count == 0:
        raise HTTPException(status_code=404, detail="No movies found")

    total_pages = ceil(total_count / per_page)

    return MovieListResponse(
        items=movies,
        total=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get(
    "/{movie_id}",
    response_model=MovieDetail,
    summary="Get movie details by ID",
    description=(
        "<h3>Fetch detailed information about a specific movie by its ID.</h3>"
        "<p>Returns all stored details for the movie if it exists, otherwise "
        "responds with a 404 error.</p>"
    ),
    responses={
        200: {"description": "Movie details retrieved successfully."},
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {"example": {"detail": "Movie not found"}}
            },
        },
    },
)
async def read_movie(
    movie_id: int = Path(..., ge=1, description="Unique movie ID"),
    session: AsyncSession = Depends(get_db),
) -> MovieDetail:
    repo = MovieRepository(session)
    movie = await repo.get_by_id(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.post(
    "/",
    response_model=MovieDetail,
    status_code=201,
    summary="Add a new movie",
    description=(
        "<h3>Create a new movie record in the database.</h3>"
        "<p>This endpoint accepts details like name, date, genres, actors, and languages.</p>"
    ),
    responses={
        201: {"description": "Movie created successfully."},
        400: {
            "description": "Invalid input.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid input data"}
                }
            },
        },
    },
)
async def create_new_movie(
    movie: MovieCreate,
    session: AsyncSession = Depends(get_db),
) -> MovieDetail:
    repo = MovieRepository(session)
    return await repo.create(movie)


@router.patch(
    "/{movie_id}",
    response_model=MovieDetail,
    summary="Update a movie by ID",
    description=(
        "<h3>Update details of an existing movie.</h3>"
        "<p>Allows partial updates of movie fields. "
        "Returns the updated movie if successful.</p>"
    ),
    responses={
        200: {"description": "Movie updated successfully."},
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {"example": {"detail": "Movie not found"}}
            },
        },
    },
)
async def update_existing_movie(
    movie_id: int = Path(..., ge=1, description="Unique movie ID"),
    movie_data: MovieUpdate = Body(..., description="Fields to update"),
    session: AsyncSession = Depends(get_db),
) -> MovieDetail:
    repo = MovieRepository(session)
    updated_movie = await repo.update(movie_id, movie_data)
    if not updated_movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return updated_movie


@router.delete(
    "/{movie_id}",
    status_code=200,
    summary="Delete a movie by ID",
    description=(
        "<h3>Delete a specific movie from the database.</h3>"
        "<p>Removes the movie if it exists; otherwise returns a 404 error.</p>"
    ),
    responses={
        200: {
            "description": "Movie deleted successfully.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie deleted successfully."}
                }
            },
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {"example": {"detail": "Movie not found"}}
            },
        },
    },
)
async def remove_movie(
    movie_id: int = Path(..., ge=1, description="Unique movie ID"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    repo = MovieRepository(session)
    deleted = await repo.delete(movie_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Movie not found")

    return {"detail": "Movie deleted successfully."}


@router.post("/like/")
async def like(
    background_tasks: BackgroundTasks,
    target_id: int,
    target_type: LikeTargetType,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> dict:
    if target_type == LikeTargetType.MOVIE:
        check_dislike = await db.execute(
            select(DislikeModel).where(
                DislikeModel.movie_id == target_id,
                DislikeModel.user_id == current_user.id,
            )
        )
        db_check_dislike = check_dislike.scalar_one_or_none()
        if db_check_dislike:
            await db.delete(db_check_dislike)
            await db.commit()

    result = await db.execute(
        select(LikeModel).where(
            LikeModel.user_id == current_user.id,
            LikeModel.target_id == target_id,
            LikeModel.target_type == target_type,
        )
    )
    existing_like = result.scalar_one_or_none()

    if existing_like:
        await db.delete(existing_like)
        await db.commit()
        return {"message": "Removed like"}

    new_like = LikeModel(
        user_id=current_user.id, target_id=target_id, target_type=target_type
    )
    db.add(new_like)
    await db.commit()

    if target_type == LikeTargetType.COMMENT:
        await notify_comment_like_user(
            db, background_tasks, target_id, email_sender
        )

    return {"message": "Liked"}


@router.post("/dislike/")
async def dislike(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> dict:

    check_like = await db.execute(
        select(LikeModel).where(
            LikeModel.target_id == movie_id,
            LikeModel.user_id == current_user.id,
        )
    )
    db_check_like = check_like.scalars().first()
    if db_check_like:
        await db.delete(db_check_like)
        await db.commit()

    check_like = await db.execute(
        select(DislikeModel).where(
            DislikeModel.movie_id == movie_id,
            DislikeModel.user_id == current_user.id,
        )
    )
    db_check_like = check_like.scalar_one_or_none()
    if db_check_like:
        await db.delete(db_check_like)
        await db.commit()
        return {"message": "Removed dislike"}

    new_dislike = DislikeModel(
        user_id=current_user.id,
        movie_id=movie_id,
    )
    db.add(new_dislike)
    await db.commit()

    return {"message": "Disliked"}


@router.post("/comment/")
async def comment(
    data: CommentCreate,
    background_tasks: BackgroundTasks,
    target_id: int,
    target_type: LikeTargetType,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> dict:

    new_comment = Comment(
        user_id=current_user.id,
        text=data.text,
        target_id=target_id,
        target_type=target_type,
    )

    if target_type == LikeTargetType.COMMENT:
        await notify_comment_like_user(
            db, background_tasks, target_id, email_sender
        )

    db.add(new_comment)
    await db.commit()

    return {"message": "Comment complete"}


@router.get("/genres/", response_model=GenreResponseList)
async def adasdasdasd(
    session: AsyncSession = Depends(get_db),
) -> GenreResponseList:
    genres = await session.execute(select(GenreModel))
    genres_db = genres.scalars().all()
    orders_list = []
    for genre in genres_db:
        counter = (
            select(func.count(MovieModel.id))
            .join(MovieModel.genres)
            .where(GenreModel.id == genre.id)
        )
        result = await session.execute(counter)
        count = result.scalar()
        orders_list.append(
            GenreBase(
                genre_name=genre.name,
                count=count,
                link=f"http://127.0.0.1:8000/api/v1/movies/?page=1&per_page=10&genre_id={genre.id}",
            )
        )

    return GenreResponseList(genres=orders_list)
