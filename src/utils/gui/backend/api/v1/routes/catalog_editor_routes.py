"""FastAPI routes for catalog editor - OS package templates and role mappings."""

import json
import logging
from fastapi import APIRouter, Depends, Query

from ....api.v1.schemas.catalog_editor_schemas import (
    BundleListResponse,
    BundleInfo,
)
from ....services.os_package_service import OSPackageService
from ....services.software_config_service import SoftwareConfigService
from ..dependencies import get_os_package_service, get_software_config_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/catalog-editor", tags=["Catalog Editor"])


@router.get("/os-packages/bundles", response_model=BundleListResponse)
async def list_os_bundles(
    arch: str = Query(...),
    os_family: str = Query(...),
    version: str = Query(...),
    os_package_service: OSPackageService = Depends(get_os_package_service)
):
    """List all available bundles for a given OS/arch/version.
    
    Returns bundle names, types (functional/infra/os), and package counts.
    
    Example:
        GET /api/v1/catalog-editor/os-packages/bundles?arch=x86_64&os_family=rhel&version=10.0
    """
    bundles = os_package_service.list_available_bundles(arch, os_family, version)
    
    bundle_infos = [
        BundleInfo(**bundle) for bundle in bundles
    ]
    
    return BundleListResponse(bundles=bundle_infos)


@router.get("/os-packages/bundle/{bundle_name}")
async def get_bundle_packages(
    bundle_name: str,
    arch: str = Query(...),
    os_family: str = Query(...),
    version: str = Query(...),
    os_package_service: OSPackageService = Depends(get_os_package_service)
):
    """Get packages from a specific bundle.
    
    Returns packages organized by section (e.g., slurm_control_node, slurm_node).
    
    Example:
        GET /api/v1/catalog-editor/os-packages/bundle/slurm_custom?arch=x86_64&os_family=rhel&version=10.0
    """
    packages = os_package_service.get_bundle_packages(arch, os_family, version, bundle_name)
    
    return {"bundle_name": bundle_name, "packages": packages}


# ─── Role/Bundle Mappings ─────────────────────────────────────

@router.get("/roles")
async def list_roles():
    """List all available roles with architecture suffixes.

    Returns the 12 predefined functional roles with architecture suffixes.

    Example:
        GET /api/v1/catalog-editor/roles
    """
    # Return the 11 predefined roles (service_kube_control_plane_first_x86_64 is not used in catalogs)
    roles = [
        'os_x86_64',
        'os_aarch64',
        'service_kube_control_plane_x86_64',
        'service_kube_node_x86_64',
        'slurm_control_node_x86_64',
        'slurm_node_x86_64',
        'slurm_node_aarch64',
        'login_node_x86_64',
        'login_node_aarch64',
        'login_compiler_node_x86_64',
        'login_compiler_node_aarch64',
    ]

    return {"roles": sorted(roles)}


@router.get("/roles/{role}/packages")
async def get_role_packages(
    role: str,
    arch: str = Query(...),
    os_family: str = Query(...),
    version: str = Query(...),
    os_package_service: OSPackageService = Depends(get_os_package_service),
    sw_config_service: SoftwareConfigService = Depends(get_software_config_service),
):
    """Get packages for a specific role.

    Strips architecture suffix from role name to match software_config.json format.
    Returns only packages from the specific role section within the bundle.
    """
    predefined_bundles = {
        'os_x86_64': ['ldms'],
        'os_aarch64': ['ldms']
    }

    if role in predefined_bundles:
        return _get_predefined_role_packages(
            role, arch, os_family, version, predefined_bundles[role], os_package_service
        )

    role_name = role.replace('_x86_64', '').replace('_aarch64', '')
    bundles = sw_config_service.get_role_bundles(role_name)
    logger.info("Role: %s, Bundles: %s", role_name, bundles)

    if not bundles:
        return {"role": role, "packages": {}}

    all_packages = {}
    for bundle_name in bundles:
        metadata = sw_config_service.get_bundle_metadata(bundle_name)
        bundle_arch = metadata.get('arch')

        if bundle_arch and arch not in bundle_arch:
            logger.info("Skipping bundle %s: arch %s not in %s", bundle_name, arch, bundle_arch)
            continue

        version_suffix = f"_v{metadata['version']}" if metadata.get('version') else ''
        actual_bundle_name = f"{bundle_name}{version_suffix}"

        packages = _load_bundle_packages(
            os_package_service, arch, os_family, version, actual_bundle_name, bundle_name
        )
        if packages:
            _merge_bundle_sections(all_packages, packages, bundle_name, role_name)

    return {"role": role, "packages": all_packages}


def _get_predefined_role_packages(
    role: str,
    arch: str,
    os_family: str,
    version: str,
    bundle_names: list[str],
    os_package_service: OSPackageService
) -> dict:
    """Get packages for predefined roles that don't have software_config.json entries."""
    all_packages = {}
    for bundle_name in bundle_names:
        try:
            bundle_packages = os_package_service.get_bundle_packages(arch, os_family, version, bundle_name)
            if bundle_name in bundle_packages:
                all_packages[bundle_name] = [
                    {**pkg, 'architecture': [arch]} for pkg in bundle_packages[bundle_name]
                ]
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
            logger.error("Failed to load bundle %s: %s", bundle_name, exc)
            continue
    return {"role": role, "packages": all_packages}


def _load_bundle_packages(
    os_package_service: OSPackageService,
    arch: str,
    os_family: str,
    version: str,
    actual_bundle_name: str,
    base_bundle_name: str
) -> dict:
    """Try loading versioned bundle; fall back to base name if not found."""
    for bundle_name in (actual_bundle_name, base_bundle_name):
        try:
            return os_package_service.get_bundle_packages(arch, os_family, version, bundle_name)
        except FileNotFoundError:
            logger.info("Bundle not found: %s", bundle_name)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.error("Failed to load bundle %s: %s", bundle_name, exc)
    return {}


def _merge_bundle_sections(
    all_packages: dict,
    bundle_packages: dict,
    bundle_name: str,
    role_name: str
) -> None:
    """Merge common and role-specific sections from bundle packages."""
    if bundle_name in bundle_packages:
        all_packages[bundle_name] = bundle_packages[bundle_name]
        logger.info("Found common section %s", bundle_name)
    if role_name in bundle_packages and role_name != bundle_name:
        if bundle_name in all_packages:
            all_packages[bundle_name] = all_packages[bundle_name] + bundle_packages[role_name]
        else:
            all_packages[role_name] = bundle_packages[role_name]
        logger.info("Found role section %s in bundle %s", role_name, bundle_name)
