"""
Configuration Service for Config Editor Module

Provides business logic for configuration management including bundles,
software config, PXE mapping, and deployment configs.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from ..config.settings import get_settings
from ..utils.file_io import read_json, write_json, read_yaml, write_yaml, read_csv, write_csv
from ..models.schemas import (
    SoftwareConfig, PXEFunctionalGroup
)
from ..core.exceptions import (
    BundleNotFoundError,
    SoftwareConfigNotFoundError,
    PXEMappingNotFoundError,
    ConfigurationNotFoundError
)
from ..core.constants import (
    FUNCTIONAL_BUNDLES, INFRA_BUNDLES, OS_BUNDLES, ALL_KNOWN_BUNDLES
)

logger = logging.getLogger(__name__)


class ConfigService:
    """Service for managing OMNIA configuration files."""

    # Path validation regex - allows only safe characters
    _SAFE_PATH_RE = re.compile(r'^[a-zA-Z0-9._-]+$')

    # PXE mapping column names
    _PXE_COLUMNS = (
        "functional_group_name", "group_name", "service_tag",
        "parent_service_tag", "hostname", "admin_mac", "admin_ip",
        "bmc_mac", "bmc_ip", "ib_nic_name", "ib_ip",
    )

    def _validate_path_component(self, value: str, name: str) -> None:
        """Validate a path component to prevent path traversal attacks.

        Args:
            value: Path component to validate
            name: Name of the parameter (for error messages)

        Raises:
            ValueError: If the value contains unsafe characters
        """
        if not self._SAFE_PATH_RE.match(value):
            raise ValueError(f"Invalid {name}: {value!r}")

    def __init__(self, settings=None):
        """Initialize the service.

        Args:
            settings: Optional settings instance. If None, uses default.
        """
        self.settings = settings or get_settings()
        self.input_dir = self.settings.output_dir
        self.config_dir = self.settings.base_input_dir / "config"

        logger.info("ConfigService initialized with input_dir: %s", self.input_dir)

    def __repr__(self) -> str:
        return f"ConfigService(input_dir={self.input_dir})"
    
    def get_available_bundles(self, architecture: str, version: str) -> List[str]:
        """Get available bundle names for specific architecture and version.

        Args:
            architecture: Architecture (x86_64 or aarch64)
            version: OS version (e.g., "10.0")

        Returns:
            List of available bundle names
        """
        self._validate_path_component(architecture, "architecture")
        self._validate_path_component(version, "version")

        bundle_dir = self.config_dir / architecture / "rhel" / version
        try:
            bundle_files = list(bundle_dir.glob("*.json"))
        except (OSError, PermissionError) as e:
            logger.warning("Failed to list bundle directory %s: %s", bundle_dir, e)
            return []

        # Use shared bundle classification constants
        bundles = []
        for file in bundle_files:
            # Extract bundle name using logic from OSPackageService._extract_bundle_name
            bundle_name = file.stem
            # Try matching a known bundle prefix
            for name in sorted(ALL_KNOWN_BUNDLES, key=len, reverse=True):
                if bundle_name == name:
                    bundle_name = name
                    break
                # Handle version suffixes like _v1.35.1, _2.16.0, -1.0
                if bundle_name.startswith(name) and len(bundle_name) > len(name):
                    sep = bundle_name[len(name)]
                    if sep in ('_', '-'):
                        # Check if next char is 'v' for versioned pattern
                        if sep == '_' and len(bundle_name) > len(name) + 1 and bundle_name[len(name) + 1] == 'v':
                            bundle_name = name
                            break
                        # Otherwise treat as generic separator
                        bundle_name = name
                        break
            bundles.append(bundle_name)
        
        return sorted(set(bundles))

    def _resolve_bundle_file(self, bundle_dir: Path, bundle_name: str) -> Path:
        """Find bundle file, handling version suffixes.

        Args:
            bundle_dir: Directory containing bundle files
            bundle_name: Base bundle name

        Returns:
            Path to the bundle file

        Raises:
            BundleNotFoundError: If no matching bundle file is found
        """
        self._validate_path_component(bundle_name, "bundle_name")

        exact = bundle_dir / f"{bundle_name}.json"
        if exact.exists():
            return exact

        # Try versioned patterns in order of specificity
        for pattern in (f"{bundle_name}_v*.json", f"{bundle_name}_*.json"):
            try:
                matches = list(bundle_dir.glob(pattern))
            except (OSError, PermissionError) as e:
                logger.warning("Failed to glob pattern %s in %s: %s", pattern, bundle_dir, e)
                continue

            if matches:
                if len(matches) > 1:
                    logger.warning(
                        "Multiple matches for %s in %s: %s",
                        bundle_name, bundle_dir, [m.name for m in matches],
                    )
                return matches[0]

        raise BundleNotFoundError(bundle_name)
    
    def get_bundle_config(self, architecture: str, version: str, bundle_name: str) -> Dict[str, Any]:
        """Get bundle configuration for specific architecture, version, and bundle.

        Args:
            architecture: Architecture (x86_64 or aarch64)
            version: OS version
            bundle_name: Bundle name

        Returns:
            Bundle configuration as dictionary
        """
        self._validate_path_component(architecture, "architecture")
        self._validate_path_component(version, "version")
        self._validate_path_component(bundle_name, "bundle_name")

        bundle_dir = self.config_dir / architecture / "rhel" / version
        bundle_file = self._resolve_bundle_file(bundle_dir, bundle_name)
        return read_json(bundle_file)
    
    def update_bundle_config(self, architecture: str, version: str, bundle_name: str,
                           config: Dict[str, Any]) -> None:
        """Update bundle configuration.

        Args:
            architecture: Architecture
            version: OS version
            bundle_name: Bundle name
            config: Updated configuration
        """
        self._validate_path_component(architecture, "architecture")
        self._validate_path_component(version, "version")
        self._validate_path_component(bundle_name, "bundle_name")

        bundle_dir = self.config_dir / architecture / "rhel" / version
        bundle_file = self._resolve_bundle_file(bundle_dir, bundle_name)
        write_json(bundle_file, config)
        logger.info("Updated bundle config: %s", bundle_file)
    
    def get_software_config(self) -> SoftwareConfig:
        """Get software configuration from software_config.json.

        Returns:
            SoftwareConfig object
        """
        software_config_file = self.input_dir / "software_config.json"
        try:
            data = read_json(software_config_file)
        except FileNotFoundError:
            logger.warning("Software config not found: %s", software_config_file)
            raise SoftwareConfigNotFoundError(str(software_config_file))
        except OSError as exc:
            logger.error("Error reading software config %s: %s", software_config_file, exc)
            raise SoftwareConfigNotFoundError(str(software_config_file))
        return SoftwareConfig(**data)
    
    def update_software_config(self, config: SoftwareConfig) -> None:
        """Update software configuration.

        Args:
            config: Updated SoftwareConfig object
        """
        software_config_file = self.input_dir / "software_config.json"
        config_dict = {
            "cluster_os_type": config.cluster_os_type,
            "cluster_os_version": config.cluster_os_version,
            "repo_config": config.repo_config,
            "softwares": config.softwares,
            "slurm_custom": config.slurm_custom,
            "service_k8s": config.service_k8s
        }
        write_json(software_config_file, config_dict)
        logger.info("Updated software config: %s", software_config_file)
    
    def get_pxe_mapping(self) -> List[PXEFunctionalGroup]:
        """Get PXE functional groups from PXE mapping file.

        Returns:
            List of PXEFunctionalGroup objects
        """
        pxe_mapping_file = self.input_dir / "pxe_mapping_file.csv"
        try:
            rows = read_csv(pxe_mapping_file)
        except FileNotFoundError:
            logger.warning("PXE mapping not found: %s", pxe_mapping_file)
            raise PXEMappingNotFoundError(str(pxe_mapping_file))
        except OSError as exc:
            logger.error("Error reading PXE mapping %s: %s", pxe_mapping_file, exc)
            raise PXEMappingNotFoundError(str(pxe_mapping_file))

        if len(rows) < 2:
            return []

        # Skip header row
        groups = []
        for row in rows[1:]:
            row_dict = dict(zip(self._PXE_COLUMNS, row))
            group = PXEFunctionalGroup(
                functional_group_name=row_dict.get("functional_group_name", ""),
                group_name=row_dict.get("group_name", ""),
                service_tag=row_dict.get("service_tag"),
                parent_service_tag=row_dict.get("parent_service_tag"),
                hostname=row_dict.get("hostname"),
                admin_mac=row_dict.get("admin_mac"),
                admin_ip=row_dict.get("admin_ip"),
                bmc_mac=row_dict.get("bmc_mac"),
                bmc_ip=row_dict.get("bmc_ip"),
                ib_nic_name=row_dict.get("ib_nic_name"),
                ib_ip=row_dict.get("ib_ip")
            )
            groups.append(group)

        return groups
    
    def update_pxe_mapping(self, groups: List[PXEFunctionalGroup]) -> None:
        """Update PXE mapping file.

        Args:
            groups: List of PXEFunctionalGroup objects
        """
        pxe_mapping_file = self.input_dir / "pxe_mapping_file.csv"

        # Header row
        rows = [[
            "FUNCTIONAL_GROUP_NAME", "GROUP_NAME", "SERVICE_TAG", "PARENT_SERVICE_TAG",
            "HOSTNAME", "ADMIN_MAC", "ADMIN_IP", "BMC_MAC", "BMC_IP", "IB_NIC_NAME", "IB_IP"
        ]]

        # Data rows
        for group in groups:
            row = [
                group.functional_group_name,
                group.group_name,
                group.service_tag or "",
                group.parent_service_tag or "",
                group.hostname or "",
                group.admin_mac or "",
                group.admin_ip or "",
                group.bmc_mac or "",
                group.bmc_ip or "",
                group.ib_nic_name or "",
                group.ib_ip or ""
            ]
            rows.append(row)

        write_csv(pxe_mapping_file, rows)
        logger.info("Updated PXE mapping: %s", pxe_mapping_file)
    
    def get_deployment_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Get deployment configuration YAML file.

        Args:
            config_name: Name of config (e.g., "network_spec", "storage_config")

        Returns:
            Configuration as dictionary, or None if not found
        """
        self._validate_path_component(config_name, "config_name")

        config_file = self.input_dir / f"{config_name}.yml"
        try:
            return read_yaml(config_file)
        except FileNotFoundError:
            logger.warning("Deployment config not found: %s", config_file)
            raise ConfigurationNotFoundError(config_name)
        except OSError as exc:
            logger.error("Error reading deployment config %s: %s", config_file, exc)
            raise ConfigurationNotFoundError(config_name)
    
    def update_deployment_config(self, config_name: str, config: Dict[str, Any]) -> None:
        """Update deployment configuration YAML file.

        Args:
            config_name: Name of config
            config: Updated configuration
        """
        self._validate_path_component(config_name, "config_name")

        config_file = self.input_dir / f"{config_name}.yml"
        write_yaml(config_file, config)
        logger.info("Updated deployment config: %s", config_file)
    
    def generate_functional_layers(self) -> list:
        """Generate functional layers from PXE mapping.

        Returns:
            List of FunctionalLayer objects
        """
        from ..models.catalog_schemas import FunctionalLayer

        pxe_groups = self.get_pxe_mapping()

        # Extract unique functional group names and create layers
        layer_names = set()
        for group in pxe_groups:
            layer_names.add(group.functional_group_name)

        layers = []
        for layer_name in sorted(layer_names):
            layer = FunctionalLayer(
                name=layer_name,
                functional_packages=[]  # Packages will be added during catalog generation
            )
            layers.append(layer)

        return layers

    def _load_preset(
        self, preset_id: str, name: str, description: str,
        scheduler: str, architecture: str, catalog_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Load a single preset configuration.

        Args:
            preset_id: Preset identifier
            name: Preset display name
            description: Preset description
            scheduler: Scheduler type
            architecture: Architecture type
            catalog_name: Catalog file name (e.g., "catalog_rhel_x86_64")

        Returns:
            Preset data dictionary or None if software config not found
        """
        examples_dir = self.settings.examples_dir
        input_dir = self.settings.output_dir

        catalog_path = examples_dir / "catalog" / f"{catalog_name}.json"
        sw_config_dir = (
            examples_dir / "catalog" / "mapping_file_software_config"
            / f"{catalog_name}_json"
        )
        sw_config_path = sw_config_dir / "software_config.json"

        try:
            software_config = read_json(sw_config_path)
        except (OSError, PermissionError):
            return None

        preset_data = {
            "id": preset_id,
            "name": name,
            "description": description,
            **software_config,
            "scheduler": scheduler,
            "architecture": architecture,
            "catalog_file": catalog_path.name if catalog_path.exists() else None,
        }

        # Load additional configuration files
        config_files = [
            ("omnia_config.yml", "omnia_config"),
            ("telemetry_config.yml", "telemetry_config"),
            ("storage_config.yml", "storage_config"),
            ("telemetry_storage_config.yml", "telemetry_storage_config"),
            ("high_availability_config.yml", "high_availability_config"),
            ("gitlab_config.yml", "gitlab_config"),
            ("build_stream_config.yml", "build_stream_config"),
            ("discovery_config.yml", "discovery_config"),
            ("local_repo_config.yml", "local_repo_config"),
            ("network_spec.yml", "network_spec")
        ]

        for filename, key in config_files:
            config_path = input_dir / filename
            try:
                preset_data[key] = read_yaml(config_path)
            except (OSError, PermissionError):
                pass  # Skip missing config files

        # Load PXE mapping file using EAFP
        for candidate in (sw_config_dir / "pxe_mapping_file.csv",
                          input_dir / "pxe_mapping_file.csv"):
            try:
                with open(candidate, encoding='utf-8') as f:
                    preset_data["pxe_mapping_file"] = f.read()
                break
            except OSError:
                continue

        # Load functional layers from catalog using EAFP
        try:
            catalog_data = read_json(catalog_path)
            if "Catalog" in catalog_data and "FunctionalLayer" in catalog_data["Catalog"]:
                preset_data["functional_layers"] = catalog_data["Catalog"]["FunctionalLayer"]
        except (OSError, PermissionError):
            pass  # Skip if catalog read fails

        return preset_data

    def list_presets(self) -> list:
        """List available configuration presets.

        Returns:
            List of preset data dictionaries
        """
        presets = []

        # Load catalog_rhel_x86_64 preset
        preset = self._load_preset(
            preset_id="rhel_x86_64",
            name="RHEL x86_64",
            description="Complete RHEL 10.0 cluster with x86_64 architecture",
            scheduler="both",
            architecture="x86_64",
            catalog_name="catalog_rhel_x86_64",
        )
        if preset:
            presets.append(preset)

        # Load catalog_rhel_aarch64_with_slurm_only preset
        preset = self._load_preset(
            preset_id="rhel_aarch64_slurm",
            name="RHEL aarch64 Slurm",
            description="Complete RHEL 10.0 Slurm cluster with aarch64 architecture",
            scheduler="slurm",
            architecture="aarch64",
            catalog_name="catalog_rhel_aarch64_with_slurm_only",
        )
        if preset:
            presets.append(preset)

        return presets
