from fastapi import FastAPI

from routes import accounts

app = FastAPI(
    title="Movies Api",
    description="Description of project"
)

base_rout = "http://127.0.0.1:8000"

api_version_prefix = "/api/v1"

app.include_router(accounts.router, prefix=f"{api_version_prefix}/accounts", tags=["User"])
