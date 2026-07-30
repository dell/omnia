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
"""
Dependency injection setup for Config Editor Module

Provides FastAPI Depends functions for service injection following best practices.
"""

from fastapi import Depends, Request

from ...config.settings import Settings, get_settings
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


