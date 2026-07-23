"""
Configuration settings for Config Editor Module

Provides environment-based configuration management using standard environment variables.
"""

import os
from typing import List
from pathlib import Path


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # API Configuration
        self.api_title = os.getenv("API_TITLE", "OMNIA Config Editor API")
        self.api_description = os.getenv("API_DESCRIPTION", "Backend API for OMNIA Configuration Editor GUI")
        self.api_version = os.getenv("API_VERSION", "1.0.0")
        self.api_prefix = os.getenv("API_PREFIX", "/api/v1")
        
        # Server Configuration
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.reload = os.getenv("RELOAD", "true").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "info")
        
        # CORS Configuration
        cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001")
        self.cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]
        self.cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
        self.cors_allow_methods = os.getenv("CORS_ALLOW_METHODS", "*").split(",")
        self.cors_allow_headers = os.getenv("CORS_ALLOW_HEADERS", "*").split(",")
        
        # Path Configuration
        self.base_dir = Path(__file__).parent.parent.parent.parent.parent  # Repository root
        self.build_stream_dir = self.base_dir / "build_stream"
        self.gui_dir = self.base_dir / "utils" / "gui"
        self.base_input_dir = self.base_dir / "input"  # Base input for bundle files (repo root/input)
        self.examples_dir = self.base_dir / "examples"
        
        # Output Configuration
        self.output_dir = self.gui_dir / "out"  # utils/gui/out
        
        # Environment
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "true").lower() == "true"


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the settings instance (for testing)."""
    global _settings
    _settings = None
