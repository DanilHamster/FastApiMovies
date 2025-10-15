from fastapi import FastAPI

from config.settings import API_VERSION_PREFIX
from routes import accounts
from routes.movies import router as movies_router

app = FastAPI(
    title="Movies Api",
    description="Description of project"
)

api_version_prefix = "/api/v1"
app.include_router(accounts.router, prefix=f"{API_VERSION_PREFIX}/accounts", tags=["User"])
app.include_router(movies_router, prefix=api_version_prefix)
