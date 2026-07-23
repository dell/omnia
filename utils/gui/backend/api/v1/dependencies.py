"""
Dependency injection setup for Config Editor Module

Provides FastAPI Depends functions for service injection following best practices.
"""

from fastapi import Depends, Request

from ...config.settings import Settings, get_settings
from ...services.config_service import ConfigService
from ...services.catalog_editor_service import CatalogEditorService
from ...services.adapter_policy_service import AdapterPolicyService
from ...services.wizard_generator_service import WizardGeneratorService
from ...services.local_repo_generator_service import LocalRepoGeneratorService
from ...services.os_package_service import OSPackageService
from ...services.software_config_service import SoftwareConfigService


# Settings dependency
def get_settings_dependency() -> Settings:
    """FastAPI dependency for settings."""
    return get_settings()


# Service dependencies
def get_config_service(
    settings: Settings = Depends(get_settings_dependency)
) -> ConfigService:
    """FastAPI dependency for ConfigService.
    
    Args:
        settings: Application settings
        
    Returns:
        ConfigService instance
    """
    return ConfigService(settings=settings)


def get_adapter_policy_service(
    settings: Settings = Depends(get_settings_dependency)
) -> AdapterPolicyService:
    """FastAPI dependency for AdapterPolicyService.
    
    Args:
        settings: Application settings
        
    Returns:
        AdapterPolicyService instance
    """
    return AdapterPolicyService(settings=settings)


def get_catalog_editor_service(request: Request) -> CatalogEditorService:
    """FastAPI dependency for CatalogEditorService.
    
    Args:
        request: FastAPI Request object for accessing app.state
        
    Returns:
        CatalogEditorService instance
    """
    return CatalogEditorService(app_state=request.app.state)


def get_wizard_generator_service(
    settings: Settings = Depends(get_settings_dependency)
) -> WizardGeneratorService:
    """FastAPI dependency for WizardGeneratorService.
    
    Args:
        settings: Application settings
        
    Returns:
        WizardGeneratorService instance
    """
    return WizardGeneratorService(settings=settings)


def get_local_repo_generator_service(
    settings: Settings = Depends(get_settings_dependency)
) -> LocalRepoGeneratorService:
    """FastAPI dependency for LocalRepoGeneratorService.

    Args:
        settings: Application settings

    Returns:
        LocalRepoGeneratorService instance
    """
    return LocalRepoGeneratorService(settings=settings)


def get_os_package_service(request: Request) -> OSPackageService:
    """FastAPI dependency for OSPackageService.
    
    Args:
        request: FastAPI Request object for accessing app.state
        
    Returns:
        OSPackageService instance (cached in app.state)
    """
    if not hasattr(request.app.state, 'os_package_service'):
        settings = get_settings()
        request.app.state.os_package_service = OSPackageService(
            config_dir=str(settings.base_input_dir / "config")
        )
    return request.app.state.os_package_service


def get_software_config_service(request: Request) -> SoftwareConfigService:
    """FastAPI dependency for SoftwareConfigService.
    
    Args:
        request: FastAPI Request object for accessing app.state
        
    Returns:
        SoftwareConfigService instance (cached in app.state)
    """
    if not hasattr(request.app.state, 'software_config_service'):
        settings = get_settings()
        request.app.state.software_config_service = SoftwareConfigService(
            config_dir=str(settings.base_input_dir)
        )
    return request.app.state.software_config_service


# Testing utilities
def reset_test_settings() -> None:
    """Reset settings singleton (for testing only)."""
    from ...config.settings import reset_settings
    reset_settings()
