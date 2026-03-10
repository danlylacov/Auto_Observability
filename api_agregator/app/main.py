"""Main FastAPI application module."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.routers import containers, hosts, prometheus

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Auto Observability API",
    description="Auto Observability API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(OperationalError)
async def database_operational_error_handler(
    _request: Request, exc: OperationalError
):
    """
    Обработчик ошибок подключения к базе данных.

    Args:
        _request: HTTP запрос (не используется)
        exc: Исключение OperationalError

    Returns:
        JSONResponse: Ответ с описанием ошибки
    """
    logger.error("Database connection error: %s", str(exc), exc_info=True)

    error_message = str(exc.orig) if hasattr(exc, 'orig') else str(exc)

    if ("Connection refused" in error_message or
            "could not connect" in error_message.lower()):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": (
                    "Database connection failed. "
                    "Please check if PostgreSQL is running and accessible."
                ),
                "error": "Database service unavailable"
            }
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"Database error: {error_message}",
            "error": "Database operation failed"
        }
    )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_request: Request, exc: SQLAlchemyError):
    """
    Обработчик общих ошибок SQLAlchemy.

    Args:
        _request: HTTP запрос (не используется)
        exc: Исключение SQLAlchemyError

    Returns:
        JSONResponse: Ответ с описанием ошибки
    """
    logger.error("SQLAlchemy error: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"Database error: {str(exc)}",
            "error": "Database operation failed"
        }
    )


app.include_router(containers.router, prefix="/api/v1/containers", tags=["containers"])
app.include_router(prometheus.router, prefix="/api/v1/prometheus", tags=["prometheus"])
app.include_router(hosts.router, prefix="/api/v1/hosts", tags=["hosts"])


@app.get("/")
async def root():
    """
    Корневой эндпоинт API.

    Returns:
        dict: Информация об API
    """
    return {
        "message": "Auto Observability API",
        "docs": "/docs",
        "version": app.version
    }


@app.get("/health")
async def health_check():
    """
    Проверка здоровья API.

    Returns:
        dict: Статус здоровья
    """
    return {"status": "healthy"}
