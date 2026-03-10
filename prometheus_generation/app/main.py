from fastapi import FastAPI

from app.routers import generate, main_config, signature

app = FastAPI(
    title="Prometheus Generation API",
    version="1.0.0",
    description="API documentation"
)

app.include_router(signature.router, prefix="/api/v1/signature", tags=["signature"])
app.include_router(generate.router, prefix="/api/v1/generate", tags=["generate"])
app.include_router(main_config.router, prefix="/api/v1/main-config", tags=["main-config"])


@app.get("/")
async def root():
    """
    Корневой эндпоинт API.

    Returns:
        dict: Информация об API
    """
    return {
        "message": "Prometheus Generation API",
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
