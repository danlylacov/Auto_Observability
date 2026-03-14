from fastapi import FastAPI

from app.routes import manage

app = FastAPI(
    title="Grafana API",
    version="1.0.0",
    description="API documentation"
)

app.include_router(manage.router, prefix="/api/v1/manage", tags=["manage"])


@app.get("/")
async def root():
    """
    Корневой эндпоинт API.

    Returns:
        dict: Информация об API
    """
    return {
        "message": "Grafana API",
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
