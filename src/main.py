from fastapi import FastAPI

from routes import accounts, admin_orders_router, orders_router, shopping_cart, profiles
from routes.movies import router as movies_router

app = FastAPI(title="Movies Api", description="Description of project")

api_version_prefix = "/api/v1"

app.include_router(
    accounts.router, prefix=f"{api_version_prefix}/accounts", tags=["User"]
)
app.include_router(
    profiles.router, prefix=api_version_prefix, tags=["Profile"]
)
app.include_router(movies_router, prefix=api_version_prefix)
app.include_router(orders_router, prefix=api_version_prefix)
app.include_router(admin_orders_router, prefix=api_version_prefix)
app.include_router(shopping_cart.router, prefix=api_version_prefix)
