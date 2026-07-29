"""
Custom middleware for Config Editor Module

Provides CORS and logging middleware.
"""

import logging
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class CORSMiddlewareConfig:
    """CORS middleware configuration based on environment."""
    
    @staticmethod
    def get_cors_origins():
        """Get allowed CORS origins from settings."""
        settings = get_settings()
        return settings.cors_origins
    
    @staticmethod
    def configure_cors(app):
        """Configure CORS middleware for the application.
        
        Args:
            app: FastAPI application instance
        """
        settings = get_settings()
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request and log details.
        
        Args:
            request: Incoming request
            call_next: Next middleware or route handler
            
        Returns:
            Response from the next middleware/route
        """
        # Skip noisy paths
        if request.url.path in ("/health", "/metrics"):
            return await call_next(request)

        # Log request
        logger.debug("Request: %s %s", request.method, request.url.path)
        
        # Process request
        response = await call_next(request)
        
        # Log response
        logger.debug("Response: %s for %s %s", response.status_code, request.method, request.url.path)
        
        return response


def configure_middleware(app):
    """Configure all middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    # Configure CORS first (outermost middleware runs first)
    CORSMiddlewareConfig.configure_cors(app)
    
    # Add logging middleware
    app.add_middleware(LoggingMiddleware)
