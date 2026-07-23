"""Schemas for catalog editor API."""

from pydantic import BaseModel
from typing import List, Dict, Optional


class PackageDefinition(BaseModel):
    """Definition of a single package."""
    package: str
    type: str  # rpm, image, git, tarball, etc.
    repo_name: Optional[str] = None
    url: Optional[str] = None
    tag: Optional[str] = None
    version: Optional[str] = None


class BundlePackages(BaseModel):
    """Packages within a bundle."""
    bundle_name: str
    packages: List[PackageDefinition]


class OSPackageTemplate(BaseModel):
    """Complete OS package template."""
    template_key: str
    bundles: Dict[str, List[PackageDefinition]]


class TemplateListResponse(BaseModel):
    """Response for listing available templates."""
    templates: List[str]


class OSCombination(BaseModel):
    """OS/arch/version combination."""
    os_family: str
    version: str
    arch: str


class BundleInfo(BaseModel):
    """Information about a bundle."""
    name: str
    type: str  # functional, infrastructure, os
    package_count: int
    sections: List[str]


class BundleListResponse(BaseModel):
    """Response for listing bundles."""
    bundles: List[BundleInfo]


class PackageSearchResult(BaseModel):
    """Result of package search."""
    package: str
    type: str
    bundle: str
    section: str
    repo_name: Optional[str] = None
    url: Optional[str] = None
    tag: Optional[str] = None
    version: Optional[str] = None


class PackageSearchResponse(BaseModel):
    """Response for package search."""
    results: List[PackageSearchResult]
