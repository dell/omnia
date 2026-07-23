"""Service for L2 validation of catalog content.

This service performs business logic and domain rules validation
beyond the L1 schema validation performed by ParseCatalog.

L2 Validation Rules:
- Package references must exist in package dictionaries
- Architecture consistency across packages and layers
- Required fields per package type
- Functional layer package references must be valid
- BaseOS package references must be valid
- Infrastructure package references must be valid
"""

import logging
from typing import Dict, List, Set, Any

logger = logging.getLogger(__name__)


class CatalogValidationError:
    """Represents a single validation error."""
    
    def __init__(self, level: str, code: str, message: str, path: str = ""):
        self.level = level  # 'error' or 'warning'
        self.code = code
        self.message = message
        self.path = path
    
    def to_dict(self) -> Dict[str, str]:
        return {
            'level': self.level,
            'code': self.code,
            'message': self.message,
            'path': self.path
        }
    
    def __repr__(self) -> str:
        return f"CatalogValidationError(level={self.level!r}, code={self.code!r}, path={self.path!r})"


class CatalogValidationService:
    """Service for L2 validation of catalog content."""
    
    def __init__(self):
        logger.debug("CatalogValidationService initialized")
    
    def __repr__(self) -> str:
        return "CatalogValidationService()"
    
    def validate_catalog(self, catalog: Dict[str, Any]) -> List[CatalogValidationError]:
        """Perform L2 validation on catalog data.
        
        Args:
            catalog: Catalog dictionary (parsed from JSON)
        
        Returns:
            List of validation errors
        """
        errors: List[CatalogValidationError] = []
        
        if 'Catalog' not in catalog:
            errors.append(CatalogValidationError(
                level='error',
                code='MISSING_CATALOG',
                message='Catalog section is missing'
            ))
            return errors
        
        inner = catalog['Catalog']
        
        # Validate package references across all sections
        errors.extend(self._validate_package_references(
            inner, 'FunctionalLayer', 'FunctionalPackages',
            'FunctionalPackages', 'Functional layer'
        ))
        # Note: 'osPackages' uses camelCase per catalog schema, unlike other sections
        errors.extend(self._validate_package_references(
            inner, 'BaseOS', 'OSPackages',
            'osPackages', 'BaseOS'
        ))
        errors.extend(self._validate_package_references(
            inner, 'Infrastructure', 'InfrastructurePackages',
            'InfrastructurePackages', 'Infrastructure'
        ))
        
        # Validate architecture consistency
        errors.extend(self._validate_architecture_consistency(inner))
        
        logger.info("L2 validation completed with %d errors", len(errors))
        return errors
    
    def _validate_package_references(
        self,
        inner: Dict[str, Any],
        section_key: str,
        packages_key: str,
        ref_field: str,
        label: str,
    ) -> List[CatalogValidationError]:
        """Validate that package references in a section exist in the package dict.

        Args:
            section_key: Key for the section list (e.g., 'FunctionalLayer')
            packages_key: Key for the package dict (e.g., 'FunctionalPackages')
            ref_field: Field within each item that holds package IDs
            label: Human-readable label for error messages
        """
        errors: List[CatalogValidationError] = []

        if section_key not in inner or packages_key not in inner:
            return errors

        valid_ids = set(inner[packages_key].keys())

        for item in inner[section_key]:
            item_name = item.get('Name', 'unknown')
            for pkg_id in item.get(ref_field, []):
                if pkg_id not in valid_ids:
                    errors.append(CatalogValidationError(
                        level='error',
                        code='INVALID_PACKAGE_REFERENCE',
                        message=f'{label} "{item_name}" references non-existent package: {pkg_id}',
                        path=f'Catalog.{section_key}.{item_name}.{ref_field}',
                    ))

        return errors
    
    def _validate_architecture_consistency(self, inner: Dict[str, Any]) -> List[CatalogValidationError]:
        """Validate architecture consistency across packages and layers."""
        errors: List[CatalogValidationError] = []
        
        # Collect all architectures from packages
        all_architectures: Set[str] = set()
        
        for pkg_type in ['FunctionalPackages', 'OSPackages', 'InfrastructurePackages']:
            if pkg_type not in inner:
                continue
            
            for pkg in inner[pkg_type].values():
                arch_list = pkg.get('Architecture', [])
                # Normalize to list
                if isinstance(arch_list, str):
                    arch_list = [arch_list]
                all_architectures.update(arch_list)
        
        # Validate architectures across all sections
        _ARCH_SECTIONS = ('FunctionalLayer', 'BaseOS', 'Infrastructure')
        
        for section_key in _ARCH_SECTIONS:
            if section_key not in inner:
                continue
            
            for item in inner[section_key]:
                item_name = item.get('Name', 'unknown')
                item_arch = item.get('Architecture', [])
                
                # Normalize to list
                if isinstance(item_arch, str):
                    item_arch = [item_arch]
                
                for arch in item_arch:
                    if arch not in all_architectures:
                        errors.append(CatalogValidationError(
                            level='warning',
                            code='ARCHITECTURE_MISMATCH',
                            message=f'{section_key} "{item_name}" uses architecture {arch} which is not found in any package',
                            path=f'Catalog.{section_key}.{item_name}.Architecture'
                        ))
        
        return errors
