from fastapi import FastAPI
from app.routers import generate

app = FastAPI(
    title="Prometheus Generation API",
    version="1.0.0",
    description="API documentation"
)


app.include_router(generate.router, prefix="/api/v1/generate", tags=["generate"])


@app.get("/")
async def root():
    return {
        "message": "Prometheus Generation API",
        "docs": "/docs",
        "version": app.version
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}