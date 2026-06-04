from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints.auth import router as auth_router

app = FastAPI(
    title="SceneIQ Compliance Platform API",
    description="Film & TV Tax Incentive Intelligence Platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://getsceneiq.com", "https://aura.getsceneiq.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "SceneIQ Compliance Platform API",
        "status": "operational",
        "version": "2.0.0",
        "documentation": "/docs",
    }

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy"}
