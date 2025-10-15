import asyncio

from sqlalchemy import func, insert, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db_contextmanager
from database.models.accounts import UserGroupEnum, UserGroupModel, UserModel, UserProfileModel
from database.models.movies import (
    CertificationModel,
    DirectorModel,
    GenreModel,
    MovieModel,
    StarModel,
)


class DatabaseSeeder:
    """Seeds the database with default users, profiles, and movies."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def _seed_user_groups(self) -> None:
        print("➡ Seeding user groups...")
        count_stmt = select(func.count(UserGroupModel.id))
        result = await self._db_session.execute(count_stmt)
        if result.scalar() == 0:
            groups = [{"name": group.value} for group in UserGroupEnum]
            await self._db_session.execute(insert(UserGroupModel).values(groups))
            await self._db_session.commit()
            print("✅ User groups created.")
        else:
            print("↩ User groups already exist, skipping.")

    async def _seed_users(self) -> None:
        print("➡ Seeding users...")
        result = await self._db_session.execute(select(func.count(UserModel.id)))
        user_count = result.scalar() or 0
        if user_count > 0:
            print("↩ Users already exist, skipping.")
            return

        groups_query = await self._db_session.execute(select(UserGroupModel))
        groups = {g.name.value: g.id for g in groups_query.scalars()}

        users_data = [
            {"email": "admin@example.com", "password": "Admin123!", "group": "admin"},
            {"email": "moderator@example.com", "password": "Moderator123!", "group": "moderator"},
            {"email": "user@example.com", "password": "User123!", "group": "user"},
        ]

        for u in users_data:
            user = UserModel.create(
                email=u["email"],
                raw_password=u["password"],
                group_id=groups[u["group"]],
            )
            user.is_active = True
            self._db_session.add(user)

        await self._db_session.commit()
        print("✅ Users created.")

        users = (await self._db_session.execute(select(UserModel))).scalars().all()
        for user in users:
            profile = UserProfileModel(
                user_id=user.id,
                first_name=user.email.split("@")[0].capitalize(),
                last_name="Tester",
                gender=None,
            )
            self._db_session.add(profile)

        await self._db_session.commit()
        print("✅ Profiles created.")

    async def _seed_movies(self) -> None:
        print("➡ Seeding movies...")

        movie_count = await self._db_session.scalar(select(func.count(MovieModel.id))) or 0
        if movie_count > 0:
            print("↩ Movies already exist, skipping.")
            return

        # Genres
        genres = ["Action", "Drama", "Comedy", "Sci-Fi", "Horror"]
        genre_models = [GenreModel(name=g) for g in genres]
        self._db_session.add_all(genre_models)

        # Stars
        stars = ["Robert Downey Jr.", "Scarlett Johansson", "Leonardo DiCaprio", "Tom Hanks"]
        star_models = [StarModel(name=s) for s in stars]
        self._db_session.add_all(star_models)

        # Directors
        directors = ["Christopher Nolan", "Steven Spielberg", "James Cameron"]
        director_models = [DirectorModel(name=d) for d in directors]
        self._db_session.add_all(director_models)

        # Certifications
        certs = ["G", "PG", "PG-13", "R"]
        cert_models = [CertificationModel(name=c) for c in certs]
        self._db_session.add_all(cert_models)

        await self._db_session.commit()

        genres_db = (await self._db_session.execute(select(GenreModel))).scalars().all()
        stars_db = (await self._db_session.execute(select(StarModel))).scalars().all()
        directors_db = (await self._db_session.execute(select(DirectorModel))).scalars().all()
        cert_db = (await self._db_session.execute(select(CertificationModel))).scalars().all()

        movies_data = [
            {
                "name": "Inception",
                "year": 2010,
                "time": 148,
                "imdb": 8.8,
                "votes": 2000000,
                "meta_score": 74,
                "gross": 829.89,
                "description": "A thief who steals corporate secrets through dream-sharing technology.",
                "price": 9.99,
                "certification": cert_db[2],
                "genres": [genres_db[1], genres_db[3]],
                "stars": [stars_db[2]],
                "directors": [directors_db[0]],
            },
            {
                "name": "Iron Man",
                "year": 2008,
                "time": 126,
                "imdb": 7.9,
                "votes": 1100000,
                "meta_score": 79,
                "gross": 585.17,
                "description": "After being held captive, Tony Stark builds a suit of armor to fight evil.",
                "price": 7.99,
                "certification": cert_db[1],
                "genres": [genres_db[0]],
                "stars": [stars_db[0]],
                "directors": [directors_db[2]],
            },
            {
                "name": "Catch Me If You Can",
                "year": 2002,
                "time": 141,
                "imdb": 8.1,
                "votes": 950000,
                "meta_score": 75,
                "gross": 352.11,
                "description":
                    "The story of Frank Abagnale Jr.,"
                    " who successfully conned millions as a pilot and doctor.",
                "price": 8.49,
                "certification": cert_db[1],
                "genres": [genres_db[1], genres_db[2]],
                "stars": [stars_db[2], stars_db[3]],
                "directors": [directors_db[1]],
            },
        ]

        for m in movies_data:
            movie = MovieModel(
                name=m["name"],
                year=m["year"],
                time=m["time"],
                imdb=m["imdb"],
                votes=m["votes"],
                meta_score=m["meta_score"],
                gross=m["gross"],
                description=m["description"],
                price=m["price"],
                certification=m["certification"],
                genres=m["genres"],
                stars=m["stars"],
                directors=m["directors"],
            )
            self._db_session.add(movie)

        await self._db_session.commit()
        print("✅ Movies created successfully.")

    async def seed_all(self) -> None:
        """Runs all seeding methods safely."""
        try:
            await self._seed_user_groups()
            await self._seed_users()
            await self._seed_movies()
            print("🎉 Database seeded successfully.")
        except SQLAlchemyError as e:
            print(f"❌ Database error: {e}")
            await self._db_session.rollback()
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            await self._db_session.rollback()


async def main() -> None:
    _ = get_settings()
    async with get_db_contextmanager() as db_session:
        seeder = DatabaseSeeder(db_session)
        await seeder.seed_all()


if __name__ == "__main__":
    asyncio.run(main())
