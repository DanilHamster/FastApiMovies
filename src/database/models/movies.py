from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy import String, Text, DECIMAL, UniqueConstraint, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship


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
        "movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column(
        "director_id", ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True, nullable=False),
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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        back_populates="certification"
    )

    def __repr__(self):
        return f"<Certification(name='{self.name}')>"


class MovieModel(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), default=uuid4, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    time: Mapped[int] = mapped_column(nullable=False)
    imdb: Mapped[float] = mapped_column(nullable=False)
    votes: Mapped[int] = mapped_column(nullable=False)
    meta_score: Mapped[float] = mapped_column(nullable=True)
    gross: Mapped[float] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10,2), nullable=False)
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="CASCADE"),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="unique_movie_name_year_time"),
    )

    def __repr__(self):
        return f"<Movie(name={self.name!r}, year={self.year}, imdb={self.imdb})>"