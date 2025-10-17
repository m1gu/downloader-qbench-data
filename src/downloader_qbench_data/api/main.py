"""FastAPI app factory for the Downloader QBench Data API."""

from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from downloader_qbench_data.config import get_settings
from .routers import entities, metrics

LOGGER = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure a FastAPI application instance."""

    settings = get_settings()
    LOGGER.info("Initialising FastAPI application for Downloader QBench Data")

    app = FastAPI(
        title="Downloader QBench Data API",
        version="1.0.0",
        description="REST API providing metrics and details for QBench data syncs.",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(metrics.router, prefix="/api/v1")
    app.include_router(entities.router, prefix="/api/v1")

    return app
