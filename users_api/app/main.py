"""FastAPI application for users and JWT auth."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.init_schema import init_schema_and_bootstrap
from app.routers import auth, users_mgmt

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        init_schema_and_bootstrap()
    except Exception:
        logger.exception("init_schema_and_bootstrap failed")
        raise
    yield


app = FastAPI(title="Users API", version="1.0.0", lifespan=lifespan)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users_mgmt.router, prefix="/api/v1/users", tags=["users"])


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/")
def root():
    return {"service": "users_api", "docs": "/docs"}
