"""
Catalog Editor routes for Config Editor Module

Provides API endpoints for direct catalog CRUD operations.
"""

import logging
from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, List

from ..dependencies import get_catalog_editor_service
from ....services.catalog_editor_service import CatalogEditorService
from ....models.catalog_schemas import (
    CatalogRoot,
    FunctionalPackage,
    InfrastructurePackage,
    FunctionalLayer,
    DriverPackage,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/catalog", tags=["catalog"])


# ─── Catalog Presets (Examples) ───────────────────────────────────────────

@router.get("/presets")
async def get_catalog_presets(
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> List[Dict[str, str]]:
    """Get list of available catalog preset files."""
    return service.list_catalog_presets()


@router.get("/presets/{filename}")
async def get_catalog_preset(
    filename: str,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> Dict[str, Any]:
    """Load a specific catalog preset file."""
    try:
        return service.load_catalog_preset(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Catalog preset not found: {filename}")


@router.post("/validate")
async def validate_catalog(
    catalog: CatalogRoot,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Validate catalog without saving."""
    return service.validate_catalog(catalog)


# ─── Functional Packages ────────────────────────────────────

@router.post("/packages/functional")
async def add_functional_package(
    pkg: FunctionalPackage,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Add a functional package (in-memory, no disk save)."""
    catalog = service.get_catalog()
    package_id = service.generate_package_id(
        pkg.Name, "functional"
    )
    catalog.Catalog.FunctionalPackages[package_id] = pkg
    logger.info("Added functional package %s, total packages: %s", package_id, len(catalog.Catalog.FunctionalPackages))
    return {"package_id": package_id, "package": pkg}


@router.put("/packages/functional/{package_id:path}")
async def update_functional_package(
    package_id: str,
    pkg: FunctionalPackage,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> FunctionalPackage:
    """Update a functional package (in-memory, no disk save)."""
    package_id = unquote(package_id)
    
    catalog = service.get_catalog()
    if package_id not in catalog.Catalog.FunctionalPackages:
        raise HTTPException(
            status_code=404, detail="Package not found"
        )
    catalog.Catalog.FunctionalPackages[package_id] = pkg
    return pkg


@router.delete("/packages/functional/{package_id:path}")
async def delete_functional_package(
    package_id: str,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Delete a functional package (in-memory, no disk save)."""
    package_id = unquote(package_id)
    
    catalog = service.get_catalog()
    if package_id not in catalog.Catalog.FunctionalPackages:
        raise HTTPException(
            status_code=404, detail="Package not found"
        )
    del catalog.Catalog.FunctionalPackages[package_id]
    return {"message": "Package deleted"}


# ─── OS Packages ────────────────────────────────────────────

@router.post("/packages/os")
async def add_os_package(
    pkg: FunctionalPackage,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Add an OS package (in-memory, no disk save)."""
    catalog = service.get_catalog()
    package_id = service.generate_package_id(pkg.Name, "os")
    catalog.Catalog.OSPackages[package_id] = pkg
    # Don't save to disk - only save on explicit user action
    return {"package_id": package_id, "package": pkg}


@router.put("/packages/os/{package_id:path}")
async def update_os_package(
    package_id: str,
    pkg: FunctionalPackage,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> FunctionalPackage:
    """Update an OS package (in-memory, no disk save)."""
    package_id = unquote(package_id)
    
    catalog = service.get_catalog()
    if package_id not in catalog.Catalog.OSPackages:
        raise HTTPException(
            status_code=404, detail="OS package not found"
        )
    catalog.Catalog.OSPackages[package_id] = pkg
    return pkg


@router.delete("/packages/os/{package_id:path}")
async def delete_os_package(
    package_id: str,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Delete an OS package (in-memory, no disk save)."""
    package_id = unquote(package_id)
    
    catalog = service.get_catalog()
    if package_id not in catalog.Catalog.OSPackages:
        raise HTTPException(
            status_code=404, detail="OS package not found"
        )
    del catalog.Catalog.OSPackages[package_id]
    return {"message": "OS package deleted"}


# ─── Infrastructure Packages ────────────────────────────────

@router.post("/packages/infrastructure")
async def add_infrastructure_package(
    pkg: InfrastructurePackage,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Add an infrastructure package (in-memory, no disk save)."""
    catalog = service.get_catalog()
    package_id = service.generate_package_id(
        pkg.Name, "infrastructure"
    )
    catalog.Catalog.InfrastructurePackages[package_id] = pkg
    # Don't save to disk - only save on explicit user action
    return {"package_id": package_id, "package": pkg}


@router.put("/packages/infrastructure/{package_id:path}")
async def update_infrastructure_package(
    package_id: str,
    pkg: InfrastructurePackage,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> InfrastructurePackage:
    """Update an infrastructure package (in-memory, no disk save)."""
    package_id = unquote(package_id)
    
    catalog = service.get_catalog()
    if package_id not in catalog.Catalog.InfrastructurePackages:
        raise HTTPException(
            status_code=404,
            detail="Infrastructure package not found",
        )
    catalog.Catalog.InfrastructurePackages[package_id] = pkg
    return pkg


@router.delete("/packages/infrastructure/{package_id:path}")
async def delete_infrastructure_package(
    package_id: str,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Delete an infrastructure package (in-memory, no disk save)."""
    package_id = unquote(package_id)
    
    catalog = service.get_catalog()
    if package_id not in catalog.Catalog.InfrastructurePackages:
        raise HTTPException(
            status_code=404,
            detail="Infrastructure package not found",
        )
    del catalog.Catalog.InfrastructurePackages[package_id]
    return {"message": "Infrastructure package deleted"}


# ─── Functional Layers ──────────────────────────────────────

@router.post("/layers")
async def add_functional_layer(
    layer: FunctionalLayer,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Add a functional layer (in-memory, no disk save)."""
    catalog = service.get_catalog()
    existing_names = [
        l.Name for l in catalog.Catalog.FunctionalLayer
    ]
    if layer.Name in existing_names:
        raise HTTPException(
            status_code=400,
            detail="Layer name already exists",
        )
    catalog.Catalog.FunctionalLayer.append(layer)
    # Don't save to disk - only save on explicit user action
    return {"message": "Layer added", "layer": layer}


@router.put("/layers/{layer_name:path}")
async def update_functional_layer(
    layer_name: str,
    layer: FunctionalLayer,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> FunctionalLayer:
    """Update a functional layer (in-memory, no disk save)."""
    layer_name = unquote(layer_name)
    
    catalog = service.get_catalog()
    for i, existing in enumerate(
        catalog.Catalog.FunctionalLayer
    ):
        if existing.Name == layer_name:
            catalog.Catalog.FunctionalLayer[i] = layer
            return layer
    # Layer doesn't exist — upsert: create it
    catalog.Catalog.FunctionalLayer.append(layer)
    logger.info("Layer %s not found, created via upsert", layer_name)
    return layer


@router.delete("/layers/{layer_name:path}")
async def delete_functional_layer(
    layer_name: str,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Delete a functional layer (in-memory, no disk save)."""
    layer_name = unquote(layer_name)
    
    catalog = service.get_catalog()
    original_count = len(catalog.Catalog.FunctionalLayer)
    catalog.Catalog.FunctionalLayer = [
        l
        for l in catalog.Catalog.FunctionalLayer
        if l.Name != layer_name
    ]
    if len(catalog.Catalog.FunctionalLayer) == original_count:
        raise HTTPException(status_code=404, detail="Layer not found")
    return {"message": "Layer deleted"}


# ─── Import / Export ────────────────────────────────────────

@router.post("/import")
async def import_catalog(
    catalog: CatalogRoot,
    request: Request,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> CatalogRoot:
    """Import a catalog from JSON (in-memory only, no disk save)."""
    validation = service.validate_catalog(catalog)
    if not validation["valid"]:
        raise HTTPException(
            status_code=422, detail=validation["errors"]
        )
    # Load catalog into memory only (no disk save)
    service.set_catalog(catalog)
    return catalog


# ─── Miscellaneous Packages ──────────────────────────────────

@router.post("/packages/miscellaneous")
async def add_miscellaneous_package(
    pkg: FunctionalPackage,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Add a miscellaneous package (in-memory, no disk save)."""
    catalog = service.get_catalog()
    package_id = service.generate_package_id(pkg.Name, "miscellaneous")
    if package_id in catalog.Catalog.FunctionalPackages:
        raise HTTPException(status_code=400, detail="Miscellaneous package ID already exists")
    catalog.Catalog.FunctionalPackages[package_id] = pkg
    catalog.Catalog.Miscellaneous.append(package_id)
    logger.info("Added miscellaneous package %s, total packages: %s", package_id, len(catalog.Catalog.FunctionalPackages))
    return {"package_id": package_id, "package": pkg}


@router.put("/packages/miscellaneous/{package_id:path}")
async def update_miscellaneous_package(
    package_id: str,
    pkg: FunctionalPackage,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> FunctionalPackage:
    """Update a miscellaneous package (in-memory, no disk save)."""
    package_id = unquote(package_id)

    catalog = service.get_catalog()
    if package_id not in catalog.Catalog.FunctionalPackages:
        raise HTTPException(
            status_code=404, detail="Package not found"
        )
    catalog.Catalog.FunctionalPackages[package_id] = pkg
    return pkg


@router.delete("/packages/miscellaneous/{package_id:path}")
async def delete_miscellaneous_package(
    package_id: str,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Delete a miscellaneous package (in-memory, no disk save)."""
    package_id = unquote(package_id)

    catalog = service.get_catalog()
    if package_id not in catalog.Catalog.FunctionalPackages:
        raise HTTPException(
            status_code=404, detail="Package not found"
        )
    del catalog.Catalog.FunctionalPackages[package_id]
    catalog.Catalog.Miscellaneous = [id for id in catalog.Catalog.Miscellaneous if id != package_id]
    return {"message": "Package deleted"}


# ─── Driver Packages ────────────────────────────────────────

@router.post("/packages/driver")
async def add_driver_package(
    pkg: DriverPackage,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Add a driver package (in-memory, no disk save)."""
    catalog = service.get_catalog()
    package_id = service.generate_package_id(
        pkg.Name, "driver"
    )
    catalog.Catalog.DriverPackages[package_id] = pkg
    # Don't save to disk - only save on explicit user action
    return {"package_id": package_id, "package": pkg}


@router.put("/packages/driver/{package_id:path}")
async def update_driver_package(
    package_id: str,
    pkg: DriverPackage,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> DriverPackage:
    """Update a driver package (in-memory, no disk save)."""
    package_id = unquote(package_id)
    
    catalog = service.get_catalog()
    if package_id not in catalog.Catalog.DriverPackages:
        raise HTTPException(
            status_code=404, detail="Driver package not found"
        )
    catalog.Catalog.DriverPackages[package_id] = pkg
    return pkg


@router.delete("/packages/driver/{package_id:path}")
async def delete_driver_package(
    package_id: str,
    service: CatalogEditorService = Depends(get_catalog_editor_service),
) -> dict:
    """Delete a driver package (in-memory, no disk save)."""
    package_id = unquote(package_id)
    
    catalog = service.get_catalog()
    if package_id not in catalog.Catalog.DriverPackages:
        raise HTTPException(
            status_code=404, detail="Driver package not found"
        )
    del catalog.Catalog.DriverPackages[package_id]
    return {"message": "Driver package deleted"}
