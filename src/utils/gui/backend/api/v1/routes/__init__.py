"""API v1 routes module."""

from .catalog_routes import router as catalog_router
from .wizard_routes import router as wizard_router
from .adapter_policy_routes import router as adapter_policy_router
from .catalog_editor_routes import router as catalog_editor_router
from .local_repo_routes import router as local_repo_router

__all__ = [
    "catalog_router",
    "wizard_router",
    "adapter_policy_router",
    "catalog_editor_router",
    "local_repo_router"
]
