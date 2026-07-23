import re
import shutil
import logging
import os
from datetime import datetime
from typing import Optional

from ..models.catalog_schemas import (
    CatalogRoot,
    CatalogInner,
    BaseOS,
    Infrastructure,
)
from ..utils.file_io import read_json, write_json_atomic
from ..config.settings import get_settings


logger = logging.getLogger(__name__)


class CatalogEditorService:
    # Path constants
    BACKUP_DIR_RELATIVE = "build_stream/core/catalog/test_fixtures/.backup"
    DEFAULT_CATALOG_PATH = "build_stream/core/catalog/test_fixtures/catalog_rhel.json"
    # Regex constants
    VERSION_PATTERN = r"(?:[-_]?v\d+(?:[-.]\d+)*$|(?:^|[-_])\d+(?:[-.]\d+)*$)"

    def __init__(self, settings=None, app_state=None):
        """Initialize the catalog editor service.
        
        Args:
            settings: Optional settings instance. If None, uses default.
            app_state: Optional FastAPI app.state for shared catalog storage.
        """
        self.settings = settings or get_settings()
        self.base_dir = self.settings.base_dir
        # Don't set a default catalog path - catalog is kept in memory
        # Only save when user explicitly clicks Save or Export JSON
        self.catalog_path = None
        self.backup_dir = (
            self.base_dir / self.BACKUP_DIR_RELATIVE
        )
        # Use app_state for shared catalog storage (if available)
        self.app_state = app_state
        self._catalog: Optional[CatalogRoot] = None

    def __repr__(self) -> str:
        return f"CatalogEditorService(base_dir={self.base_dir}, catalog_path={self.catalog_path})"

    def get_catalog(self) -> CatalogRoot:
        """Get the catalog (in-memory, no file load required)."""
        if self.app_state and hasattr(self.app_state, 'catalog'):
            catalog = self.app_state.catalog
            if catalog is None:
                # Start with empty catalog if none exists
                catalog = self._create_empty_catalog()
                self.app_state.catalog = catalog
                logger.info("Created new empty catalog in app.state")
            return catalog
        else:
            # Fallback to instance catalog for backward compatibility
            if self._catalog is None:
                self._catalog = self._create_empty_catalog()
                logger.info("Created new empty catalog in instance")
            return self._catalog

    def get_inner(self) -> CatalogInner:
        """Convenience: return the inner catalog data."""
        return self.get_catalog().Catalog

    def set_catalog(self, catalog: CatalogRoot) -> None:
        """Set the catalog in-memory (no disk save)."""
        self._catalog = catalog
        if self.app_state and hasattr(self.app_state, 'catalog'):
            self.app_state.catalog = catalog

    def save_catalog(self, catalog: CatalogRoot, path: str = None) -> None:
        """Save catalog with atomic write and backup.
        
        Args:
            catalog: The catalog to save
            path: Optional path to save to. If None, uses default catalog_path
        """
        save_path = path or self.catalog_path
        if save_path is None:
            # Use a default path if none specified
            save_path = str(
                self.base_dir / self.DEFAULT_CATALOG_PATH
            )
        
        # Prevent path traversal attacks
        resolved = os.path.realpath(save_path)
        if not resolved.startswith(str(self.base_dir.resolve())):
            raise ValueError(f"Save path outside allowed directory: {save_path!r}")
        
        catalog_dict = catalog.model_dump(mode="json", exclude_none=True)
        write_json_atomic(save_path, catalog_dict)
        # Update app_state.catalog if available
        if self.app_state and hasattr(self.app_state, 'catalog'):
            self.app_state.catalog = catalog
        # Update instance catalog to ensure refetch gets updated data
        self._catalog = catalog
        logger.info("Catalog saved to %s", save_path)

    def validate_catalog(self, catalog: CatalogRoot) -> dict:
        """Validate catalog structure and return validation results (L1 + L2)."""
        errors: list[str] = []
        warnings: list[str] = []
        inner = catalog.Catalog

        # Check for duplicate package IDs across categories
        all_ids_list = (
            list(inner.FunctionalPackages.keys())
            + list(inner.OSPackages.keys())
            + list(inner.InfrastructurePackages.keys())
        )
        seen = set()
        duplicates = set()
        for pid in all_ids_list:
            if pid in seen:
                duplicates.add(pid)
            seen.add(pid)
        if duplicates:
            errors.append(
                f"Duplicate package IDs across categories: "
                f"{', '.join(sorted(duplicates))}"
            )

        # Warn about packages with no Sources
        for pkg_id, pkg in inner.FunctionalPackages.items():
            if pkg.Sources is None and pkg.Type not in (
                "pip_module",
                "image",
            ):
                warnings.append(
                    f"Functional package '{pkg_id}' has no Sources"
                )

        # L2 validation using CatalogValidationService (handles package references)
        try:
            from .catalog_validation_service import CatalogValidationService
            # Perform L2 business logic validation
            l2_service = CatalogValidationService()
            catalog_dict = catalog.model_dump(mode="json", exclude_none=True)
            l2_errors = l2_service.validate_catalog(catalog_dict)

            for l2_error in l2_errors:
                if l2_error.level == 'error':
                    errors.append(f"[L2] {l2_error.code}: {l2_error.message}")
                else:
                    warnings.append(f"[L2] {l2_error.code}: {l2_error.message}")
        except ImportError as e:
            logger.warning("L2 validation service not available: %s", e)
        except (ValueError, TypeError, AttributeError) as e:
            logger.error("L2 validation failed: %s", e)
            # Don't fail the entire validation if L2 fails

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def generate_package_id(
        self,
        package_name: str,
        category: str = "functional",
    ) -> str:
        """
        Generate human-readable package ID with cross-category
        collision detection matching the _1 suffix pattern used
        in the real catalog.
        """
        # Sanitize the base name: lowercase, no spaces, normalize slashes for safety
        base_id = package_name.lower().replace(" ", "-").replace("/", "-")

        # Remove version-like suffixes from the original package name to get a
        # stable package ID (e.g. "csi-powerscale-v2.17.0" -> "csi-powerscale").
        # Slashes are preserved in the candidate so image package IDs stay intact.
        candidate = re.sub(self.VERSION_PATTERN, "", package_name, flags=re.IGNORECASE)
        if not candidate:
            candidate = re.sub(self.VERSION_PATTERN, "", base_id, flags=re.IGNORECASE)
        if not candidate:
            candidate = package_name

        # Check for collisions across ALL categories
        inner = self.get_inner()
        existing_ids = (
            set(inner.FunctionalPackages.keys())
            | set(inner.OSPackages.keys())
            | set(inner.InfrastructurePackages.keys())
        )

        if candidate not in existing_ids:
            return candidate

        # Handle collisions with _N suffix
        counter = 1
        while f"{candidate}_{counter}" in existing_ids:
            counter += 1
        return f"{candidate}_{counter}"

    def _create_empty_catalog(self) -> CatalogRoot:
        """Create empty catalog structure matching real format."""
        return CatalogRoot(
            Catalog=CatalogInner(
                Name="Catalog",
                Version="1.0",
                Identifier="image-build",
                # CatalogSchemaVersion: Not set for Schema 1.0 compatibility
                FunctionalLayer=[],
                BaseOS=[
                    BaseOS(
                        Name="RHEL", Version="10.0", osPackages=[]
                    )
                ],
                Infrastructure=[
                    Infrastructure(
                        Name="csi", InfrastructurePackages=[]
                    )
                ],
                FunctionalPackages={},
                OSPackages={},
                InfrastructurePackages={},
            )
        )

    def _create_backup(self) -> None:
        """Create timestamped backup of current catalog."""
        if self.catalog_path is None:
            return  # No catalog to backup
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = (
            self.backup_dir / f"catalog_rhel_{timestamp}.json"
        )

        if self.catalog_path.exists():
            shutil.copy2(self.catalog_path, backup_path)
    
    def list_catalog_presets(self) -> list:
        """List available catalog preset files from examples/catalog folder.
        
        Returns:
            List of catalog preset file information
        """
        examples_dir = self.settings.examples_dir / "catalog"
        
        if not examples_dir.exists():
            logger.warning("Examples catalog directory not found: %s", examples_dir)
            return []
        
        catalog_files = []
        for file_path in examples_dir.glob("*.json"):
            catalog_files.append({
                "name": file_path.stem,
                "filename": file_path.name,
            })
        
        # Sort alphabetically
        catalog_files.sort(key=lambda x: x["name"])
        logger.info("Found %d catalog preset files", len(catalog_files))
        return catalog_files
    
    def load_catalog_preset(self, filename: str) -> dict:
        """Load a specific catalog preset file.
        
        Args:
            filename: Name of the preset file to load
            
        Returns:
            Catalog data as dictionary
            
        Raises:
            FileNotFoundError: If preset file not found
        """
        examples_dir = (self.settings.examples_dir / "catalog").resolve()
        catalog_path = (examples_dir / filename).resolve()
        
        # Prevent path traversal attacks
        if not str(catalog_path).startswith(str(examples_dir)):
            raise ValueError(f"Invalid filename: {filename!r}")
        
        if not catalog_path.exists():
            raise FileNotFoundError(f"Catalog preset not found: {filename}")
        
        catalog_data = read_json(catalog_path)
        logger.info("Loaded catalog preset: %s", filename)
        return catalog_data
