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

from api.logging_utils import log_secure_info
from api.router import api_router
from container import container
from orchestrator.cleanup.scheduler import AutoCleanupScheduler

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

container.wire(modules=[
    "api.jobs.routes",
    "api.jobs.dependencies",
    "api.local_repo.routes",
    "api.local_repo.dependencies",
    "api.restart.routes",
    "api.restart.dependencies",
    "api.validate.routes",
    "api.validate.dependencies",
])
log_secure_info('info', f"Using container: {container.__class__.__name__}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage application lifecycle events.

    Starts the result poller and, with the SQL-backed (prod) container, the
    automatic image cleanup scheduler on startup; stops both on shutdown.
    """
    # Startup: Start the result poller
    result_poller = container.result_poller()
    await result_poller.start()

    # Automatic cleanup needs the SQL repositories, so it runs in prod only.
    cleanup_scheduler = None
    if os.getenv("ENV", "prod").lower() == "prod":
        cleanup_scheduler = AutoCleanupScheduler()
        await cleanup_scheduler.start()
    log_secure_info('info', "Application startup complete")

    yield

    # Shutdown: Stop the cleanup scheduler and the result poller
    if cleanup_scheduler is not None:
        await cleanup_scheduler.stop()
    await result_poller.stop()
    log_secure_info('info', "Application shutdown complete")


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
    log_secure_info('error', "Unhandled exception occurred", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "message": "An internal server error occurred"},
    )


def get_server_config():
    """Get server host and port configuration with proper validation."""
    server_host = os.getenv(
        "HOST", "0.0.0.0"  # nosec B104 — container must bind all interfaces
    )

    # Validate host is not empty or just whitespace
    if not server_host or server_host.strip() == "":
        raise ValueError("HOST environment variable cannot be empty")

    # Port validation
    port_env = os.getenv("PORT")
    if not port_env:
        raise ValueError("PORT environment variable is required")

    try:
        server_port = int(port_env)
        if 1 > server_port or server_port > 65535:
            raise ValueError(f"Port {server_port} is not in valid range 1-65535")
    except ValueError as exc:
        if "invalid literal" in str(exc):
            raise ValueError(
                f"PORT environment variable must be a valid integer, got: {port_env}"
            ) from exc
        raise

    return server_host.strip(), server_port


if __name__ == "__main__":
    import uvicorn  # pylint: disable=import-outside-toplevel

    try:
        _host, _port = get_server_config()

        log_secure_info('info', f"Starting Build Stream API server on {_host}:{_port}")

        uvicorn.run("main:app", host=_host, port=_port)
    except ValueError as val_err:
        raise ValueError("Invalid server configuration") from val_err
    except Exception as run_err:
        raise RuntimeError("Internal server error") from run_err
