import asyncio
import logging
import sys
from contextlib import asynccontextmanager

# On Windows, Playwright requires ProactorEventLoop for subprocesses
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers.chat import router as chat_router
from app.routers.health import router as health_router
from app.services.cdp_manager import cdp_manager


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger("gemini_cdp.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI application lifecycle manager."""
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Checking CDP availability on %s...", settings.CDP_URL)

    # Initial non-blocking CDP check
    try:
        status_info = await cdp_manager.check_status()
        if status_info["connected"]:
            logger.info("Initial connection to Chrome established successfully.")
        else:
            logger.warning(
                "Chrome not detected yet on %s. "
                "Make sure Chrome is running with remote debugging port 9222.",
                settings.CDP_URL,
            )
    except Exception as exc:
        logger.warning("Deferred initial CDP connection: %s", exc)

    yield

    logger.info("Shutting down API and releasing Playwright resources...")
    await cdp_manager.close()
    logger.info("Resources released successfully.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI interface to automate Google Gemini Web interactions via Chrome DevTools Protocol (CDP).",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    """Welcome root endpoint."""
    return {
        "message": f"{settings.APP_NAME} operational.",
        "documentation": "/docs",
        "cdp_status": "/cdp/status",
    }

