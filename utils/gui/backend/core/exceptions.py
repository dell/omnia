"""
Custom exception classes for Config Editor Module

Provides domain-specific exceptions for better error handling and user feedback.
"""

from typing import Optional, Any


class ConfigEditorException(Exception):
    """Base exception for Config Editor errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationNotFoundError(ConfigEditorException):
    """Raised when a configuration file is not found."""
    
    def __init__(self, config_name: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            f"Configuration not found: {config_name}",
            status_code=404,
            details=details
        )
        self.config_name = config_name


class CatalogNotFoundError(ConfigEditorException):
    """Raised when a catalog file is not found."""
    
    def __init__(self, catalog_path: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            f"Catalog file not found: {catalog_path}",
            status_code=404,
            details=details
        )
        self.catalog_path = catalog_path


class AdapterPolicyNotFoundError(ConfigEditorException):
    """Raised when an adapter policy is not found."""
    
    def __init__(self, policy_type: str = "custom", details: Optional[dict[str, Any]] = None):
        super().__init__(
            f"Adapter policy not found: {policy_type}",
            status_code=404,
            details=details
        )
        self.policy_type = policy_type


class InvalidConfigurationError(ConfigEditorException):
    """Raised when configuration data is invalid."""
    
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            f"Invalid configuration: {message}",
            status_code=400,
            details=details
        )


class GenerationError(ConfigEditorException):
    """Raised when configuration generation fails."""
    
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            f"Configuration generation failed: {message}",
            status_code=500,
            details=details
        )


class PXEMappingNotFoundError(ConfigEditorException):
    """Raised when PXE mapping file is not found."""
    
    def __init__(self, mapping_path: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            f"PXE mapping file not found: {mapping_path}",
            status_code=404,
            details=details
        )
        self.mapping_path = mapping_path


class SoftwareConfigNotFoundError(ConfigEditorException):
    """Raised when software config file is not found."""
    
    def __init__(self, config_path: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            f"Software config file not found: {config_path}",
            status_code=404,
            details=details
        )
        self.config_path = config_path


class BundleNotFoundError(ConfigEditorException):
    """Raised when a bundle is not found."""
    
    def __init__(self, bundle_name: str, arch: Optional[str] = None, details: Optional[dict[str, Any]] = None):
        arch_str = f" (arch: {arch})" if arch else ""
        super().__init__(
            f"Bundle not found: {bundle_name}{arch_str}",
            status_code=404,
            details=details
        )
        self.bundle_name = bundle_name
        self.arch = arch


class FunctionalLayerNotFoundError(ConfigEditorException):
    """Raised when a functional layer is not found."""
    
    def __init__(self, layer_name: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            f"Functional layer not found: {layer_name}",
            status_code=404,
            details=details
        )
        self.layer_name = layer_name
