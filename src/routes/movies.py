from math import ceil

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.session_sqlite import get_session
from repositories.movies import MovieRepository
from schemas.movies import MovieCreate, MovieDetail, MovieListResponse, MovieUpdate

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("/", response_model=MovieListResponse)
async def list_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> MovieListResponse:
    repo = MovieRepository(session)
    skip = (page - 1) * per_page
    movies, total_count = await repo.get_all(skip=skip, limit=per_page)

    total_pages = ceil(total_count / per_page) if total_count > 0 else 1

    return MovieListResponse(
        items=movies,
        total=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get("/{movie_id}", response_model=MovieDetail)
async def read_movie(
    movie_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
) -> MovieDetail:
    repo = MovieRepository(session)
    movie = await repo.get_by_id(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.post("/", response_model=MovieDetail, status_code=201)
async def create_new_movie(
    movie: MovieCreate,
    session: AsyncSession = Depends(get_session),
) -> MovieDetail:
    repo = MovieRepository(session)
    return await repo.create(movie)


@router.patch("/{movie_id}", response_model=MovieDetail)
async def update_existing_movie(
    movie_id: int = Path(..., ge=1),
    movie_data: MovieUpdate = Body(),
    session: AsyncSession = Depends(get_session),
) -> MovieDetail:
    repo = MovieRepository(session)
    updated_movie = await repo.update(movie_id, movie_data)
    if not updated_movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return updated_movie


@router.delete("/{movie_id}", status_code=204)
async def remove_movie(
    movie_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
) -> None:
    repo = MovieRepository(session)
    deleted = await repo.delete(movie_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Movie not found")
    return