from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from app.routers import containers
from app.routers import prometheus, hosts
import logging

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
async def database_operational_error_handler(request: Request, exc: OperationalError):
    """
    Обработчик ошибок подключения к базе данных
    """
    logger.error(f"Database connection error: {str(exc)}", exc_info=True)
    
    error_message = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
    
    if "Connection refused" in error_message or "could not connect" in error_message.lower():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "Database connection failed. Please check if PostgreSQL is running and accessible.",
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
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    """
    Обработчик общих ошибок SQLAlchemy
    """
    logger.error(f"SQLAlchemy error: {str(exc)}", exc_info=True)
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
    return {
        "message": "Auto Observability API",
        "docs": "/docs",
        "version": app.version
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}