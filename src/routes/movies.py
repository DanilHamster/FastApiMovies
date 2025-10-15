from math import ceil

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from fastapi_filter import FilterDepends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from filters.filter_movies import MovieFilter
from repositories.movies import MovieRepository
from schemas.movies import MovieCreate, MovieDetail, MovieListResponse, MovieUpdate

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
)
async def list_movies(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=100, description="Movies per page (1–100)"),
    filters: MovieFilter = FilterDepends(MovieFilter),
    session: AsyncSession = Depends(get_db),
) -> MovieListResponse:
    repo = MovieRepository(session)
    skip = (page - 1) * per_page

    movies, total_count = await repo.filter_movies(filters=filters, skip=skip, limit=per_page)

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
            "content": {"application/json": {"example": {"detail": "Movie not found"}}},
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
            "content": {"application/json": {"example": {"detail": "Invalid input data"}}},
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
            "content": {"application/json": {"example": {"detail": "Movie not found"}}},
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
