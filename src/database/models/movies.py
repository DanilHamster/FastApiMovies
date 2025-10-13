import datetime
from enum import Enum
from tkinter.constants import CASCADE
from typing import Optional

from sqlalchemy import String, Float, Text, DECIMAL, UniqueConstraint, Date, ForeignKey, Table, Column
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from sqlalchemy import Enum as SQLAlchemyEnum

from database import Base

MoviesGenresModel = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)


MovieStarsModel = Table(
    "movie_stars",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column(
        "star_id",
        ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True, nullable=False),
)


MovieDirectorsModel = Table(
    "movie_directors",
    Base.metadata,
    Column(
        "movie_id", ForeignKey("movies.id"), primary_key=True, nullable=False),
    Column(
        "director_id", ForeignKey("directors.id"), primary_key=True, nullable=False),
)

class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MoviesGenresModel,
        back_populates="genres"
    )

    def __repr__(self):
        return f"<Genre(name='{self.name}')>"


class StarModel(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MovieStarsModel,
        back_populates="stars"
    )

    def __repr__(self):
        return f"<Star(name='{self.name}')>"


class DirectorModel(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MovieDirectorsModel,
        back_populates="directors"
    )

    def __repr__(self):
        return f"<Director(name='{self.name}')>"


class CertificationModel(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        back_populates="certification"
    )


class MovieModel(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)