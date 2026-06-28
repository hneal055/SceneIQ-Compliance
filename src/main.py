"""
SceneIQ - Tax Incentive Intelligence for Film & TV
"""
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.utils.config import settings
from src.utils.database import prisma
from src.utils.auth_utils import hash_password
from src.utils.seed import run_migrations, seed_all
from src.utils.scheduler import start_scheduler, stop_scheduler
from src.api.routes import router
from src.api.largo import router as largo_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ADMIN_EMAIL = "admin@sceneiq.com"
ADMIN_PASSWORD = "sceneiq2024"

async def _ensure_user_columns() -> None:
    """Idempotently ensure the account-lockout/profile columns exist on the
    deployed app's OWN database, before any typed query selects them.

    The Prisma client (regenerated from schema.prisma) SELECTs these columns on
    every users query, so they must exist or all user queries 500. Running this
    against prisma's connection guarantees it targets the same DB the app uses,
    regardless of which database that is.
    """
    statements = [
        'ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "failedLoginCount" INTEGER NOT NULL DEFAULT 0',
        'ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "lockedUntil" TIMESTAMP(3)',
        'ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "lastLoginAt" TIMESTAMP(3)',
        'ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "fullName" TEXT',
    ]
    for sql in statements:
        await prisma.execute_raw(sql)
    logger.info("âœ… Ensured users lockout/profile columns exist")


async def _seed_admin() -> None:
    count = await prisma.user.count()
    if count == 0:
        await prisma.user.create(data={"email": ADMIN_EMAIL, "passwordHash": hash_password(ADMIN_PASSWORD), "role": "admin", "isActive": True})
        logger.info(f"âœ… Admin user created: {ADMIN_EMAIL}")
    else:
        logger.info("â„¹ï¸  Admin user already exists â€” skipping seed")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ðŸŽ¬ Starting SceneIQ")
    try:
        run_migrations()
        await prisma.connect()
        logger.info("âœ… Database connected")
        await _ensure_user_columns()
        await _seed_admin()
        await seed_all()
    except Exception as e:
        logger.warning(f"âš ï¸  Database init failed: {e}")
    try:
        start_scheduler()
    except Exception as e:
        logger.error(f"âŒ Scheduler failed to start: {e}")
    yield
    logger.info("ðŸ›‘ Shutting down SceneIQ")
    stop_scheduler()
    try:
        if prisma.is_connected():
            await prisma.disconnect()
    except Exception as e:
        logger.error(f"âŒ Database disconnection failed: {e}")

app = FastAPI(
    title="SceneIQ API",
    description="Tax Incentive Intelligence for Film & TV Productions",
    version="v1",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(router, prefix=f"/api/{settings.API_VERSION}")
app.include_router(largo_router)

@app.get("/health", tags=["Health"])
async def health_check():
    try:
        await prisma.query_raw("SELECT 1")
        return {"status": "healthy", "database": "connected", "version": settings.API_VERSION}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "disconnected", "error": str(e)})

backend_static = Path(__file__).parent.parent / "backend" / "static"
if backend_static.exists():
    app.mount("/static", StaticFiles(directory=str(backend_static)), name="static")
    logger.info(f"âœ… Static demo pages mounted from {backend_static}")
else:
    logger.warning(f"âš ï¸  Backend static directory not found at {backend_static}")

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logger.info(f"âœ… Frontend mounted from {frontend_dist}")
else:
    logger.warning("âš ï¸  Frontend dist not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host=settings.APP_HOST, port=settings.APP_PORT, log_level=settings.LOG_LEVEL.lower())





