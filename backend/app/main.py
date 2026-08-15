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

    app.include_router(chat_router, prefix="/api", tags=["Chat"])
    app.include_router(products_router, prefix="/api", tags=["Products"])

    return app


app = create_app()
