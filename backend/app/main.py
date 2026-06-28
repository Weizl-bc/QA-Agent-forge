"""FastAPI application entry point."""

from fastapi import FastAPI

from backend.app.api.router import api_router
from backend.app.core.exception import register_exception_handlers


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="QA Agent Forge API",
        description="Backend API for the QA Agent Forge platform.",
        version="0.1.0",
    )
    application.include_router(api_router, prefix="/api/v1")
    register_exception_handlers(application)
    return application


app = create_app()
