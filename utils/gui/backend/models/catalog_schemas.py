from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum


class PackageType(str, Enum):
    """All package types found in the real catalog."""
    RPM = "rpm"
    RPM_REPO = "rpm_repo"
    TARBALL = "tarball"
    ISO = "iso"
    GIT = "git"
    IMAGE = "image"
    PIP_MODULE = "pip_module"
    MANIFEST = "manifest"


class SupportedOSInfo(BaseModel):
    Name: str
    Version: str


class PackageSource(BaseModel):
    Architecture: str
    RepoName: Optional[str] = None
    Uri: Optional[str] = None


class FunctionalPackage(BaseModel):
    """
    Base package schema for Schema 1.0.
    
    Schema 1.0 fields:
    - Name, Type, Architecture: Required
    - SupportedOS: Optional (omitted by some package types like pip_module)
    - Sources: Optional (omitted by pip_module packages)
    - Version: Optional (not always available from bundle files)
    - Tag: Optional (only for image packages)
    
    Schema 1.1 fields (to be added later):
    - ApplicableFunctionalLayers: Maps packages to functional layers
    - Config: Enhanced package metadata
    - SupportedFunctions: Function metadata
    """
    Name: str
    Type: PackageType
    Architecture: List[str]
    SupportedOS: Optional[List[SupportedOSInfo]] = None
    Sources: Optional[List[PackageSource]] = None
    Version: Optional[str] = None
    Tag: Optional[str] = None

# OS packages share the same schema as functional packages
OSPackage = FunctionalPackage

class InfrastructurePackage(BaseModel):
    """
    Infrastructure package schema for Schema 1.0.
    
    Schema 1.0 fields (based on core/catalog/parser.py):
    - Name, Type, SupportedFunctions: Required
    - Architecture: Optional (defaults to [])
    - Uri: Optional (defaults to "")
    - Sources: Optional (defaults to [])
    - Version: Optional
    - Tag: Optional (defaults to "")
    
    Schema 1.1 fields (to be added later):
    - ApplicableFunctionalLayers: Maps packages to functional layers
    - Config: Enhanced package metadata
    """
    Name: str
    Type: PackageType
    Architecture: List[str] = []
    SupportedFunctions: List[Dict[str, str]] = []
    Uri: str = ""
    Sources: Optional[List[PackageSource]] = None
    Version: Optional[str] = None
    Tag: str = ""


class DriverConfig(BaseModel):
    """Driver-specific configuration fields."""
    DriverBrand: Optional[str] = None
    DriverType: Optional[str] = None


class DriverPackage(BaseModel):
    """
    Driver package schema for Schema 1.0.
    
    Schema 1.0 fields (based on core/catalog/parser.py):
    - Name, Type, Architecture, Uri, Version, Config: Required
    - Tag: Not used by parser
    - Sources: Not used by parser
    
    Schema 1.1 fields (to be added later):
    - ApplicableFunctionalLayers: Maps driver packages to functional layers
    """
    Name: str
    Type: PackageType
    Architecture: List[str]
    Uri: str
    Config: DriverConfig = Field(default_factory=DriverConfig)
    Version: str


class Driver(BaseModel):
    """
    Driver layer entry with name and package references.
    """
    Name: str
    DriverPackages: List[str]


class MiscellaneousPackage(BaseModel):
    """
    Miscellaneous package schema for Schema 1.0.
    
    Schema 1.0 fields:
    - Name, Type, Architecture, Uri: Required
    - Version: Optional
    - Tag: Optional
    - SupportedOS: Optional
    - Sources: Optional
    
    Schema 1.1 fields (to be added later):
    - ApplicableFunctionalLayers: Maps miscellaneous packages to functional layers
    - Config: Enhanced package metadata
    """
    Name: str
    Type: PackageType
    Architecture: List[str]
    Uri: str
    Version: Optional[str] = None
    Tag: Optional[str] = None
    SupportedOS: Optional[List[SupportedOSInfo]] = None
    Sources: Optional[List[PackageSource]] = None


class FunctionalLayer(BaseModel):
    """
    Functional layer schema for Schema 1.0.
    
    Schema 1.0 fields:
    - Name: Layer name
    - FunctionalPackages: Array of package ID references
    
    Schema 1.1 fields (to be added later):
    - ApplicableFunctionalLayers: Maps layer to other layers (optional)
    """
    Name: str
    FunctionalPackages: List[str]


class BaseOS(BaseModel):
    Name: str
    Version: str
    osPackages: List[str]


class Infrastructure(BaseModel):
    Name: str
    InfrastructurePackages: List[str]


class CatalogInner(BaseModel):
    """
    The real catalog nests ALL data under a single "Catalog" key.
    Metadata fields (Name, Version, Identifier) sit alongside
    FunctionalLayer, FunctionalPackages, etc.
    
    Schema 1.0 fields:
    - Name: "Catalog" (default)
    - Version: "1.0" (default)
    - Identifier: "image-build" (default)
    - FunctionalLayer: Array of functional layer definitions
    - BaseOS: Array of OS package definitions
    - Infrastructure: Array of infrastructure definitions
    - Drivers: Array of driver category definitions
    - DriverPackages: Dictionary of driver package definitions
    - FunctionalPackages: Dictionary of functional package definitions
    - OSPackages: Dictionary of OS package definitions
    - InfrastructurePackages: Dictionary of infrastructure package definitions
    - Miscellaneous: Array of miscellaneous package references
    
    Schema 1.1 fields (to be added later):
    - CatalogSchemaVersion: "1.1" when using Schema 1.1 features
    - MiscellaneousPackages: Dictionary of miscellaneous package definitions with ApplicableFunctionalLayers
    """
    # Metadata (Schema 1.0)
    Name: str = "Catalog"
    Version: str = "1.0"
    Identifier: str = "image-build"
    # CatalogSchemaVersion: Not set for Schema 1.0 compatibility (to be added in Schema 1.1)

    # Structural sections (Schema 1.0)
    FunctionalLayer: List[FunctionalLayer]
    BaseOS: List[BaseOS]
    Infrastructure: List[Infrastructure]
    Drivers: List[Driver] = []
    DriverPackages: Dict[str, DriverPackage] = {}
    FunctionalPackages: Dict[str, FunctionalPackage]
    OSPackages: Dict[str, OSPackage]
    InfrastructurePackages: Dict[str, InfrastructurePackage]
    Miscellaneous: List[str] = []
    # MiscellaneousPackages: Not set for Schema 1.0 compatibility (to be added in Schema 1.1)


class CatalogRoot(BaseModel):
    """Top-level wrapper matching the real JSON: { "Catalog": { ... } }"""
    Catalog: CatalogInner
