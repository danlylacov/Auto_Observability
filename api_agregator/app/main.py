from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import containers
from app.routers import prometheus

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


app.include_router(containers.router, prefix="/api/v1/containers", tags=["containers"])
app.include_router(prometheus.router, prefix="/api/v1/prometheus", tags=["prometheus"])


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