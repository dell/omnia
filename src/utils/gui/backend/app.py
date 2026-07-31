# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
FastAPI application for Config Editor Module (Refactored)

This is a production-ready FastAPI service with proper structure,
middleware, dependency injection, and configuration management.
"""

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.v1.routes import (
    adapter_policy_routes,
    catalog_editor_router,
    catalog_routes,
    local_repo_routes,
    wizard_routes,
)
from .config.logging import setup_logging
from .config.settings import get_settings
from .core.exceptions import ConfigEditorException
from .core.middleware import configure_middleware
from .services.job_store import JobStore

# Setup logging
settings = get_settings()
setup_logging(level=settings.log_level)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure middleware
configure_middleware(app)

# Initialize app state
app.state.job_store = JobStore(max_concurrent_jobs=3)
logger.info("Initialized JobStore in app.state")
app.state.catalog = None
logger.info("Initialized catalog in app.state")

# Include routers
api_prefix = settings.api_prefix
app.include_router(
    adapter_policy_routes.router,
    prefix=api_prefix, tags=["adapter-policy"],
)
app.include_router(
    catalog_routes.router,
    prefix=api_prefix, tags=["catalog"],
)
app.include_router(
    wizard_routes.router,
    prefix=f"{api_prefix}/config", tags=["wizard"],
)
app.include_router(
    local_repo_routes.router,
    prefix=f"{api_prefix}/local-repo", tags=["local-repo"],
)
app.include_router(
    catalog_editor_router,
    prefix=api_prefix, tags=["catalog-editor"],
)


# Exception handlers
@app.exception_handler(ConfigEditorException)
async def config_editor_exception_handler(request, exc: ConfigEditorException):
    """Handle custom ConfigEditorException."""
    logger.error("ConfigEditorException: %s", exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.error("Validation error: %s", exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": exc.errors()
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    logger.error("HTTP exception: %s - %s", exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            # Never expose exception details
            "details": None,
        }
    )


# Root endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": settings.api_title,
        "version": settings.api_version,
        "status": "running",
        "environment": settings.environment
    }


@app.get("/test-simple")
async def test_simple():
    """Simple test endpoint (only available in debug mode)."""
    if not settings.debug:
        raise StarletteHTTPException(status_code=404, detail="Not found")
    return {"message": "Simple test working", "data": "test"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting %s...", settings.api_title)
    uvicorn.run(
        "backend.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level
    )
