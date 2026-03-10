from fastapi import FastAPI

from app.routers import discover, manage

app = FastAPI(
    title="Docker API",
    version="1.0.0",
    description="API documentation"
)


app.include_router(discover.router, prefix="/api/v1/discover", tags=["discover"])
app.include_router(manage.router, prefix="/api/v1/manage", tags=["manage"])


@app.get("/")
async def root():
    """
    Корневой эндпоинт API.

    Returns:
        dict: Информация об API
    """
    return {
        "message": "Docker API",
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