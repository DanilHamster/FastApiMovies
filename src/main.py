from fastapi import FastAPI

from config.settings import API_VERSION_PREFIX
from routes import accounts

app = FastAPI(
    title="Movies Api",
    description="Description of project"
)

app.include_router(accounts.router, prefix=f"{API_VERSION_PREFIX}/accounts", tags=["User"])
