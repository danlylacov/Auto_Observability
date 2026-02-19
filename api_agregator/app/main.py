from fastapi import FastAPI
from app.routers import discover, manage

app = FastAPI(
    title="Auto Observability API",
    description="Auto Observability API",
    version="1.0.0"
)


app.include_router(discover.router, prefix="/api/v1/discover", tags=["discover"])
app.include_router(manage.router, prefix="/api/v1/manage", tags=["manage"])

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