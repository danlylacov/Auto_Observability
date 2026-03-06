from fastapi import FastAPI
from app.routes import manage

app = FastAPI(
    title="Prometheus manage API",
    version="1.0.0",
    description="API documentation"
)

app.include_router(manage.router, prefix="/api/v1/manage", tags=["manage"])



@app.get("/")
async def root():
    return {
        "message": "Prometheus manage API",
        "docs": "/docs",
        "version": app.version
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
