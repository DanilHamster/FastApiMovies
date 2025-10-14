from fastapi import APIRouter, Depends, HTTPException, Path, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.movies import MovieRepository
from database.session_sqlite import get_session
from schemas.movies import MovieCreateSchema, MovieUpdateSchema, MovieReadSchema

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("/", response_model=list[MovieReadSchema])
async def list_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    repo = MovieRepository(session)
    skip = (page - 1) * per_page
    return await repo.get_all(skip=skip, limit=per_page)


@router.get("/{movie_id}", response_model=MovieReadSchema)
async def read_movie(movie_id: int = Path(..., ge=1), session: AsyncSession = Depends(get_session)):
    repo = MovieRepository(session)
    movie = await repo.get_by_id(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.post("/", response_model=MovieReadSchema)
async def create_new_movie(movie: MovieCreateSchema, session: AsyncSession = Depends(get_session)):
    repo = MovieRepository(session)
    return await repo.create(movie)


@router.patch("/{movie_id}", response_model=MovieReadSchema)
async def update_existing_movie(
    movie_id: int = Path(..., ge=1),
    movie_data: MovieUpdateSchema = Body(),
    session: AsyncSession = Depends(get_session),
):
    repo = MovieRepository(session)
    updated_movie = await repo.update(movie_id, movie_data)
    if not updated_movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return updated_movie


@router.delete("/{movie_id}", status_code=204)
async def remove_movie(movie_id: int = Path(..., ge=1), session: AsyncSession = Depends(get_session)):
    repo = MovieRepository(session)
    deleted = await repo.delete(movie_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Movie not found")
    return
