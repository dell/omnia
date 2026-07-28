"""Schemas for catalog editor API."""

from pydantic import BaseModel
from typing import List


class BundleInfo(BaseModel):
    """Information about a bundle."""
    name: str
    type: str  # functional, infrastructure, os
    package_count: int
    sections: List[str]


class BundleListResponse(BaseModel):
    """Response for listing bundles."""
    bundles: List[BundleInfo]
