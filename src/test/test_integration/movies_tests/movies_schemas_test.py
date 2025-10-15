from uuid import uuid4

import pytest
from pydantic import ValidationError

from schemas.movies import (
    CertificationBase,
    CertificationResponse,
    DirectorBase,
    DirectorResponse,
    GenreBase,
    GenreResponse,
    MovieBase,
    MovieCreate,
    MovieDetail,
    MovieList,
    MovieListResponse,
    MovieUpdate,
    StarBase,
    StarResponse,
)


def test_genre_base_and_response():
    genre = GenreBase(name="Action")
    assert genre.name == "Action"

    genre_resp = GenreResponse(id=1, name="Action")
    assert genre_resp.id == 1
    assert genre_resp.name == "Action"


def test_star_base_and_response():
    star = StarBase(name="Keanu Reeves")
    assert star.name == "Keanu Reeves"

    star_resp = StarResponse(id=1, name="Keanu Reeves")
    assert star_resp.id == 1


def test_director_base_and_response():
    director = DirectorBase(name="Wachowski")
    assert director.name == "Wachowski"

    director_resp = DirectorResponse(id=1, name="Wachowski")
    assert director_resp.id == 1


def test_certification_base_and_response():
    cert = CertificationBase(name="PG-13")
    assert cert.name == "PG-13"

    cert_resp = CertificationResponse(id=1, name="PG-13")
    assert cert_resp.id == 1


def test_movie_base_validation():
    movie = MovieBase(
        name="Matrix",
        year=1999,
        time=136,
        imdb=8.7,
        votes=1800000,
        meta_score=73.0,
        gross=463.5,
        description="Sci-fi action",
        price=12.5,
        certification_id=1
    )
    assert movie.name == "Matrix"
    assert movie.imdb <= 10.0

    with pytest.raises(ValidationError):
        MovieBase(
            name="Bad Movie",
            year=1800,
            time=0,
            imdb=12.0,
            votes=-5,
            description="x" * 5001,
            price=-1,
            certification_id=0
        )


def test_movie_create_and_update():
    movie_create = MovieCreate(
        name="Matrix",
        year=1999,
        time=136,
        imdb=8.7,
        votes=1800000,
        description="Sci-fi action",
        price=12.5,
        certification_id=1,
        genres=["Action", "Sci-Fi"],
        stars=["Keanu Reeves"],
        directors=["Wachowski"]
    )
    assert "Action" in movie_create.genres
    assert "Keanu Reeves" in movie_create.stars

    movie_update = MovieUpdate(
        name="Matrix Reloaded",
        genres=["Action"],
        stars=[]
    )
    assert movie_update.name == "Matrix Reloaded"
    assert movie_update.genres == ["Action"]


def test_movie_detail():
    detail = MovieDetail(
        id=1,
        uuid=uuid4(),
        name="Matrix",
        year=1999,
        time=136,
        imdb=8.7,
        votes=1800000,
        description="Sci-fi action",
        price=12.5,
        certification_id=1,
        genres=[GenreResponse(id=1, name="Action")],
        stars=[StarResponse(id=1, name="Keanu Reeves")],
        directors=[DirectorResponse(id=1, name="Wachowski")],
        certification=CertificationResponse(id=1, name="PG-13")
    )
    assert detail.genres[0].name == "Action"
    assert detail.stars[0].name == "Keanu Reeves"
    assert detail.directors[0].name == "Wachowski"


def test_movie_list_and_response():
    movie_item = MovieList(id=1, name="Matrix", year=1999, imdb=8.7, price=12.5)
    assert movie_item.name == "Matrix"

    response = MovieListResponse(
        items=[movie_item],
        total=1,
        page=1,
        per_page=10,
        total_pages=1,
        has_next=False,
        has_prev=False
    )
    assert response.total == 1
    assert response.items[0].name == "Matrix"
