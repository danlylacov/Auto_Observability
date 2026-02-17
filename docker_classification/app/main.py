from fastapi import FastAPI
from app.routers import classificate

app = FastAPI(
    title="Docker classification API",
    version="1.0.0",
    description="API documentation"
)


app.include_router(classificate.router, prefix="/api/v1/classificate", tags=["classificate"])


@app.get("/")
async def root():
    return {
        "message": "Docker classification API",
        "docs": "/docs",
        "version": app.version
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}