import logging

from fastapi import FastAPI

from app.routers import generate, main_config, signature
from app.services.main_config import MainPrometheusConfig

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Prometheus Generation API",
    version="1.0.0",
    description="API documentation"
)

app.include_router(signature.router, prefix="/api/v1/signature", tags=["signature"])
app.include_router(generate.router, prefix="/api/v1/generate", tags=["generate"])
app.include_router(main_config.router, prefix="/api/v1/main-config", tags=["main-config"])


@app.on_event("startup")
async def startup_event():
    """
    Инициализация при старте приложения.
    
    Проверяет наличие основного конфига Prometheus в MinIO
    и создает его при первом запуске, если он отсутствует.
    """
    try:
        config = MainPrometheusConfig()
        main_config = config.minio_client.get_yaml_file('mainConfig/prometheus.yml')
        
        if main_config is None:
            print("INFO: Основной конфиг Prometheus не найден. Создаю базовый конфиг...")
            logger.info("Основной конфиг Prometheus не найден. Создаю базовый конфиг...")
            config.first_init()
            print("INFO: Базовый конфиг Prometheus успешно создан в MinIO")
            logger.info("Базовый конфиг Prometheus успешно создан в MinIO")
        else:
            print("INFO: Основной конфиг Prometheus найден в MinIO")
            logger.info("Основной конфиг Prometheus найден в MinIO")
    except Exception as e:
        print(f"ERROR: Ошибка при инициализации конфига Prometheus: {e}")
        logger.error(f"Ошибка при инициализации конфига Prometheus: {e}", exc_info=True)
        # Не прерываем запуск приложения, если не удалось инициализировать конфиг


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
