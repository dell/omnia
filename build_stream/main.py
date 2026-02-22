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

"""Build Stream API Server.

Main entry point for the Build Stream API application.
This module initializes the FastAPI application and is invoked from the Dockerfile.

Usage:
    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.router import api_router
from container import container

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

container.wire(modules=[
    "api.jobs.routes",
    "api.jobs.dependencies",
    "api.local_repo.routes",
    "api.local_repo.dependencies",
])
logger.info("Using container: %s", container.__class__.__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle events.
    
    Starts the result poller on startup and stops it on shutdown.
    """
    # Startup: Start the result poller
    result_poller = container.result_poller()
    await result_poller.start()
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown: Stop the result poller
    await result_poller.stop()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Build Stream API",
    description="RESTful API for the Omnia Build Stream application",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Attach container to app so dependency_injector Provide dependencies resolve
app.container = container

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get(
    "/",
    summary="Root endpoint",
    description="Returns a welcome message and API documentation URL.",
)
async def root() -> dict:
    """Root endpoint returning welcome message."""
    return {
        "message": "Welcome to Build Stream API",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get(
    "/health",
    summary="Health check",
    description="Returns the health status of the API server.",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> dict:
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):  # pylint: disable=unused-argument
    """Global exception handler for unhandled exceptions."""
    logger.exception("Unhandled exception occurred")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "message": "An internal server error occurred"},
    )


def get_server_config():
    """Get server host and port configuration with proper validation."""
    host = os.getenv("HOST", "0.0.0.0")
    
    # Validate host is not empty or just whitespace
    if not host or host.strip() == "":
        raise ValueError("HOST environment variable cannot be empty")
    
    # Port validation
    port_env = os.getenv("PORT")
    if not port_env:
        raise ValueError("PORT environment variable is required")
    
    try:
        port = int(port_env)
        if not (1 <= port <= 65535):
            raise ValueError(f"Port {port} is not in valid range 1-65535")
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"PORT environment variable must be a valid integer, got: {port_env}")
        raise
    
    return host.strip(), port


if __name__ == "__main__":
    import uvicorn

    try:
        host, port = get_server_config()

        logger.info("Starting Build Stream API server on %s:%d", host, port)
        
        uvicorn.run("main:app", host=host, port=port)
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        raise
    except Exception as e:
        logger.error("Failed to start server: %s", e)
        raise
