from enum import Enum
from uuid import uuid4

from sqlalchemy import DECIMAL, Column, ForeignKey, String, Table, Text, UniqueConstraint, select, func, literal, and_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref, column_property, foreign, remote

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
        secondary=MoviesGenresModel
    )

    def __repr__(self) -> str:
        return f"<Genre(name='{self.name}')>"


class StarModel(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MovieStarsModel
    )

    def __repr__(self) -> str:
        return f"<Star(name='{self.name}')>"


class DirectorModel(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MovieDirectorsModel
    )

    def __repr__(self) -> str:
        return f"<Director(name='{self.name}')>"


class CertificationModel(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        back_populates="certification",
        passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Certification(name='{self.name}')>"


class LikeTargetType(str, Enum):
    MOVIE = "movie"
    COMMENT = "comment"


class LikeModel(Base):
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[LikeTargetType] = mapped_column(String(10), nullable=False)
    target_id: Mapped[int] = mapped_column(nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="likes")


    def __repr__(self):
        return f"<Like user_id={self.user_id} target_type={self.target_type} target_id={self.target_id}>"


class DislikeModel(Base):
    __tablename__ = "dislikes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("movie_id", "user_id", name="unique_movie_user_dislike"),
    )

    movie = relationship("MovieModel", back_populates="dislikes")
    user = relationship("UserModel", back_populates="dislikes")

    def __repr__(self):
        return f"<Dislike movie_id={self.movie_id} user_id={self.user_id}>"

class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    target_type: Mapped[LikeTargetType] = mapped_column(String(10), nullable=False)
    target_id: Mapped[int] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(String(255), nullable=False)

    likes: Mapped[list["LikeModel"]] = relationship(
        "LikeModel",
        primaryjoin=and_(
            foreign(LikeModel.target_id) == id,
            LikeModel.target_type == "comment"
        ),
        viewonly=True
    )

    like_count: Mapped[int] = column_property(
        select(func.count(LikeModel.id))
        .where(
            (LikeModel.target_type == literal("comment")) &
            (LikeModel.target_id == foreign(id))
        )
        .correlate_except(LikeModel)
        .scalar_subquery()
    )

    replies: Mapped[list["Comment"]] = relationship(
        "Comment",
        primaryjoin=and_(
            foreign(target_id) == id,
            target_type == "comment"
        ),
        viewonly=True
    )

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="comments")

    def __repr__(self):
        return (
            f"<Comment id={self.id} user_id={self.user_id} "
            f"target_type={self.target_type} target_id={self.target_id}>"
        )


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
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="CASCADE"),
        nullable=False
    )

    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        primaryjoin=and_(
            foreign(Comment.target_id) == id,
            Comment.target_type == "movie"
        ),
        viewonly=True,
        lazy="selectin"
    )


    likes: Mapped[list["LikeModel"]] = relationship(
        "LikeModel",
        primaryjoin="and_(foreign(LikeModel.target_id)==MovieModel.id, LikeModel.target_type=='movie')",
        viewonly=True,
        cascade="all, delete-orphan"
    )

    dislikes = relationship(
        "DislikeModel",
        back_populates="movie",
        cascade="all, delete-orphan"
    )

    like_count = column_property(
        select(func.count(LikeModel.id))
        .where(
            (LikeModel.target_type == literal("movie")) &
            (LikeModel.target_id == id)
        )
        .correlate_except(LikeModel)
        .scalar_subquery()
    )

    dislike_count = column_property(
        select(func.count(DislikeModel.id))
        .where(DislikeModel.movie_id == id)
        .correlate_except(DislikeModel)
        .scalar_subquery()
    )

    genres: Mapped[list["GenreModel"]] = relationship(
        "GenreModel",
        secondary=MoviesGenresModel,
        back_populates="movies",
        lazy="selectin"
    )

    stars: Mapped[list["StarModel"]] = relationship(
        "StarModel",
        secondary=MovieStarsModel,
        back_populates="movies",
        lazy="selectin"
    )

    directors: Mapped[list["DirectorModel"]] = relationship(
        "DirectorModel",
        secondary=MovieDirectorsModel,
        back_populates="movies",
        lazy="selectin"
    )

    certification: Mapped["CertificationModel"] = relationship(
        "CertificationModel",
        back_populates="movies",
        passive_deletes=True
    )

    order_items: Mapped[list["OrderItemModel"]] = relationship(
        "OrderItemModel", back_populates="movie"
    )

    cart_items: Mapped[list["CartItemModel"]] = relationship(
        "CartItemModel", back_populates="movie"
    )

    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="unique_movie_name_year_time"),
    )

    def __repr__(self) -> str:
        return f"<Movie(name={self.name!r}, year={self.year}, imdb={self.imdb})>"
