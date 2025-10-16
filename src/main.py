from fastapi import FastAPI
from config.settings import API_VERSION_PREFIX
from routes import (
    accounts,
    admin_orders_router,
    orders_router,
    shopping_cart,
    profiles,
)
from routes.movies import router as movies_router

app = FastAPI(title="Movies Api", description="Description of project")

app.include_router(accounts.router, prefix=f"{API_VERSION_PREFIX}/accounts", tags=["User"])
app.include_router(profiles.router, prefix=API_VERSION_PREFIX, tags=["Profile"])
app.include_router(movies_router, prefix=API_VERSION_PREFIX)
app.include_router(orders_router, prefix=API_VERSION_PREFIX)
app.include_router(admin_orders_router, prefix=API_VERSION_PREFIX)
app.include_router(shopping_cart.router, prefix=API_VERSION_PREFIX)
