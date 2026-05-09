from fastapi import FastAPI

from app.routers import dashboard

app = FastAPI(
    title="Grafana Generation API",
    version="1.0.0",
    description="Скачивание шаблонов дашбордов с grafana.com и подготовка к импорту",
)

app.include_router(dashboard.router, prefix="/api/v1/grafana", tags=["grafana-dashboards"])


@app.get("/")
async def root():
    return {
        "message": "Grafana Generation API",
        "docs": "/docs",
        "version": app.version,
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
