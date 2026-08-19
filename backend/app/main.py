"""FastAPI application entrypoint for LifeGift Agricultural Product Chatbot."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifespan context."""
    settings = get_settings()
    logger.info("Starting LifeGift Chatbot API in %s mode", settings.APP_ENV)
    yield
    logger.info("Shutting down LifeGift Chatbot API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()
    app = FastAPI(
        title="LifeGift Chatbot QA API",
        description="AI product recommendation and grounded QA chatbot for LifeGift agricultural products.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["System"])
    async def health_check():
        """Service health check endpoint."""
        return {
            "status": "ok",
            "service": "lifegift-chatbot",
            "environment": settings.APP_ENV,
        }

    # Lazy import and register routers
    from backend.app.api.chat import router as chat_router
    from backend.app.api.products import router as products_router
    from backend.app.api.coupons import router as coupons_router

    app.include_router(chat_router, prefix="/api", tags=["Chat"])
    app.include_router(products_router, prefix="/api", tags=["Products"])
    app.include_router(coupons_router, prefix="/api", tags=["Coupons"])

    # Mount static files and web interface
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    static_dir = Path(__file__).parent / "static"

    if frontend_dist.exists():
        assets_dir = frontend_dist / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/", include_in_schema=False)
        async def root():
            return FileResponse(str(frontend_dist / "index.html"))

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        if not frontend_dist.exists():
            @app.get("/", include_in_schema=False)
            async def fallback_root():
                return FileResponse(str(static_dir / "index.html"))

    return app



app = create_app()
