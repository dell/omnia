"""Service for dynamically extracting OS packages from config files.

This service reads the actual config JSON files from input/config/
and extracts package definitions based on bundle membership.

It categorizes packages as:
- Functional: service_k8s, slurm_custom, additional_packages
- Infrastructure: csi_driver_powerscale
- OS (BaseOS): default_packages, admin_debug_packages, openldap, openmpi, ucx, ldms, nfs
"""

import json
import os
import re
import threading
from collections.abc import Iterator
from typing import Any, Dict, List, Optional
import logging

from ..core.constants import FUNCTIONAL_BUNDLES, INFRA_BUNDLES, OS_BUNDLES

logger = logging.getLogger(__name__)

# Safe path component regex to prevent path traversal
_SAFE_PATH_RE = re.compile(r'^[a-zA-Z0-9._-]+$')


class OSPackageService:
    """Service for extracting OS packages from config directory.
    
    This service reads the actual config JSON files from input/config/
    and extracts package definitions based on bundle membership.
    
    It categorizes packages as:
    - Functional: service_k8s, slurm_custom, additional_packages
    - Infrastructure: csi_driver_powerscale
    - OS (BaseOS): default_packages, admin_debug_packages, openldap, openmpi, ucx, ldms, nfs
    """

    # Use shared bundle classification constants
    _FUNCTIONAL_BUNDLES = FUNCTIONAL_BUNDLES
    _INFRA_BUNDLES = INFRA_BUNDLES
    _OS_BUNDLES = OS_BUNDLES

    # Version regex for extracting bundle names
    _VERSION_RE = re.compile(r'^[\d]+(\.[\d]+)*$')

    # URL version extraction patterns (compiled for performance)
    _URL_VERSION_PATTERNS = [
        re.compile(r'/refs/tags/v?([\d.]+)'),
        re.compile(r'/[\w-]+-([\d.]+)\.tar\.gz'),
        re.compile(r'version=([\d.]+)'),
        re.compile(r'/(\d+\.\d+(?:[-.][\d.]+)*)/'),  # requires at least major.minor
    ]

    # Pre-sorted known bundles for efficient matching
    _ALL_KNOWN_BUNDLES = tuple(
        sorted(
            _FUNCTIONAL_BUNDLES | _INFRA_BUNDLES | _OS_BUNDLES,
            key=len,
            reverse=True,
        )
    )

    # Fallback regex for version suffix stripping
    _VERSION_SUFFIX_RE = re.compile(r'[-_]v?\d+(\.\d+)*$')
    
    def __init__(self, settings=None, config_dir: Optional[str] = None):
        """Initialize service with settings or config directory path.

        Args:
            settings: Settings instance with base_input_dir path
            config_dir: Direct config directory path (for backward compatibility).
                      When using settings, the path is settings.base_input_dir / "config".

        Raises:
            ValueError: If both settings and config_dir are provided.
        """
        from ..config.settings import get_settings

        if settings is not None and config_dir is not None:
            raise ValueError("Provide 'settings' or 'config_dir', not both")

        if config_dir is not None:
            self.config_dir = config_dir
            self.settings = None
        else:
            self.settings = settings or get_settings()
            self.config_dir = str(self.settings.base_input_dir / "config")

        self._json_cache: Dict[str, dict] = {}
        self._lock = threading.Lock()
        logger.debug("OSPackageService initialized with config_dir: %s", self.config_dir)

    def __repr__(self) -> str:
        return f"OSPackageService(config_dir={self.config_dir!r})"
    
    def list_available_combinations(self) -> List[Dict[str, str]]:
        """List all available OS/arch/version combinations.

        Returns:
            List of dictionaries with os_family, version, arch keys

        Example:
            [
                {"os_family": "rhel", "version": "10.0", "arch": "x86_64"},
                {"os_family": "rhel", "version": "10.0", "arch": "aarch64"}
            ]
        """
        combinations = []

        try:
            entries = os.listdir(self.config_dir)
        except FileNotFoundError:
            logger.warning("Config directory does not exist: %s", self.config_dir)
            return combinations
        except OSError as exc:
            logger.error("Error listing config directory %s: %s", self.config_dir, exc)
            return combinations

        for arch in entries:
            arch_path = os.path.join(self.config_dir, arch)
            if not os.path.isdir(arch_path):
                continue

            try:
                os_families = os.listdir(arch_path)
            except OSError:
                continue

            for os_family in os_families:
                os_family_path = os.path.join(arch_path, os_family)
                if not os.path.isdir(os_family_path):
                    continue

                try:
                    versions = os.listdir(os_family_path)
                except OSError:
                    continue

                for version in versions:
                    version_path = os.path.join(os_family_path, version)
                    # Note: using os.path.isdir here is acceptable for filesystem enumeration
                    # where TOCTOU risk is minimal and directory structure is trusted
                    if os.path.isdir(version_path):
                        combinations.append({
                            "os_family": os_family,
                            "version": version,
                            "arch": arch
                        })

        logger.info("Found %d OS combinations", len(combinations))
        return sorted(combinations, key=lambda x: (x['os_family'], x['version'], x['arch']))
    
    def list_available_bundles(
        self,
        arch: str,
        os_family: str,
        version: str
    ) -> List[Dict[str, Any]]:
        """List all available bundles for a given OS/arch/version.
        
        Args:
            arch: Architecture (x86_64, aarch64)
            os_family: OS family (rhel, ubuntu)
            version: OS version (10.0, 9.5)
        
        Returns:
            List of bundle dictionaries with name, type, package_count
            
        Example:
            [
                {"name": "default_packages", "type": "os", "package_count": 38},
                {"name": "admin_debug_packages", "type": "os", "package_count": 54},
                {"name": "service_k8s", "type": "functional", "package_count": 120}
            ]
        """
        self._validate_path_component(arch, "arch")
        self._validate_path_component(os_family, "os_family")
        self._validate_path_component(version, "version")

        config_path = os.path.join(self.config_dir, arch, os_family, version)

        try:
            files = os.listdir(config_path)
        except FileNotFoundError:
            logger.warning("Config path does not exist: %s", config_path)
            return []
        except OSError as exc:
            logger.error("Error listing config path %s: %s", config_path, exc)
            return []

        bundles = []

        for file in files:
            if not file.endswith('.json'):
                continue
            
            bundle_name, _ = os.path.splitext(file)
            file_path = os.path.join(config_path, file)
            
            try:
                data = self._load_json_cached(file_path)
                package_count = self._count_packages(data)

                bundle_type = self._classify_bundle(bundle_name)

                bundles.append({
                    "name": bundle_name,
                    "type": bundle_type,
                    "package_count": package_count,
                    "sections": list(data.keys())
                })
            except (json.JSONDecodeError, OSError, KeyError, TypeError) as exc:
                logger.error("Error reading %s: %s", file, exc)
        
        return sorted(bundles, key=lambda x: x['name'])
    
    def get_bundle_packages(
        self,
        arch: str,
        os_family: str,
        version: str,
        bundle_name: str
    ) -> Dict[str, List[Dict]]:
        """Get packages from a specific bundle, organized by section.
        
        Args:
            arch: Architecture
            os_family: OS family
            version: OS version
            bundle_name: Bundle name (e.g., "default_packages")
        
        Returns:
            Dictionary mapping section names to package lists
            
        Example:
            {
                "default_packages": [
                    {"package": "systemd", "type": "rpm", "repo_name": "baseos"},
                    {"package": "kernel", "type": "rpm", "repo_name": "baseos"}
                ]
            }
        """
        self._validate_path_component(arch, "arch")
        self._validate_path_component(os_family, "os_family")
        self._validate_path_component(version, "version")
        self._validate_path_component(bundle_name, "bundle_name")

        config_path = os.path.join(self.config_dir, arch, os_family, version, f"{bundle_name}.json")

        try:
            data = self._load_json_cached(config_path)
        except FileNotFoundError:
            logger.warning("Bundle file does not exist: %s", config_path)
            return {}
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Error reading bundle %s: %s", bundle_name, exc)
            return {}
        
        result = {}
        for section_name, pkg in self._iter_packages(data):
            package_data = self._build_package_data(pkg)
            result.setdefault(section_name, []).append(package_data)

        return result
    
    def _extract_version_from_url(self, url: str) -> Optional[str]:
        """Extract version from a tarball URL.

        Args:
            url: The URL to extract version from

        Returns:
            Extracted version string or None if not found
        """
        for pattern in self._URL_VERSION_PATTERNS:
            match = pattern.search(url)
            if match:
                return match.group(1)

        return None
    
    def get_os_packages(
        self,
        arch: str,
        os_family: str,
        version: str,
        include_bundles: Optional[set[str]] = None
    ) -> Dict[str, List[Dict]]:
        """Get all OS packages (non-functional, non-infra).

        Args:
            arch: Architecture
            os_family: OS family
            version: OS version
            include_bundles: Optional set of specific bundle names to include.
                          If None, includes all OS bundles.

        Returns:
            Dictionary mapping bundle names to package lists

        Example:
            {
                "default_packages": [...],
                "admin_debug_packages": [...],
                "openldap": [...]
            }
        """
        # Note: list_available_bundles and get_bundle_packages also validate,
        # but we validate here too for fail-fast on direct calls.
        self._validate_path_component(arch, "arch")
        self._validate_path_component(os_family, "os_family")
        self._validate_path_component(version, "version")

        # list_available_bundles already validates and lists the directory
        all_bundles = self.list_available_bundles(arch, os_family, version)
        os_bundles = [
            b for b in all_bundles
            if b['type'] == 'os' and (include_bundles is None or b['name'] in include_bundles)
        ]
        
        result = {}
        for bundle in os_bundles:
            bundle_packages = self.get_bundle_packages(arch, os_family, version, bundle['name'])
            result.update(bundle_packages)
        
        return result
    
    def search_packages(
        self,
        arch: str,
        os_family: str,
        version: str,
        query: str
    ) -> List[Dict]:
        """Search for packages across all bundles.

        Args:
            arch: Architecture
            os_family: OS family
            version: OS version
            query: Search term (package name substring). Empty string matches all packages.

        Returns:
            List of matching packages with bundle and section info

        Example:
            [
                {
                    "package": "systemd",
                    "type": "rpm",
                    "bundle": "default_packages",
                    "section": "default_packages",
                    "repo_name": "baseos"
                }
            ]
        """
        self._validate_path_component(arch, "arch")
        self._validate_path_component(os_family, "os_family")
        self._validate_path_component(version, "version")

        config_path = os.path.join(self.config_dir, arch, os_family, version)

        try:
            files = os.listdir(config_path)
        except FileNotFoundError:
            return []
        except OSError as exc:
            logger.error("Error listing config path %s: %s", config_path, exc)
            return []

        results = []
        query_lower = query.lower()

        for file in files:
            if not file.endswith('.json'):
                continue
            
            bundle_name, _ = os.path.splitext(file)
            file_path = os.path.join(config_path, file)
            
            try:
                data = self._load_json_cached(file_path)

                for section_name, pkg in self._iter_packages(data):
                    if query_lower in pkg['package'].lower():
                        result_item = self._build_package_data(pkg)
                        result_item["bundle"] = bundle_name
                        result_item["section"] = section_name
                        results.append(result_item)
            except (json.JSONDecodeError, OSError, KeyError, TypeError) as exc:
                logger.error("Error searching in %s: %s", file, exc)
        
        return sorted(results, key=lambda x: x['package'])
    
    def reload(self) -> None:
        """Force re-read from disk on the next access.

        Thread-safe: concurrent readers will see either the old
        cached value or wait for a fresh load after invalidation.
        """
        with self._lock:
            self._json_cache.clear()

    # Private helper methods

    def _validate_path_component(self, value: str, name: str) -> None:
        """Reject path components containing traversal characters."""
        if not _SAFE_PATH_RE.match(value):
            raise ValueError(f"Invalid {name}: {value!r}")

    def _load_json_cached(self, filepath: str) -> dict:
        """Load and cache JSON file with thread-safety.

        Callers MUST NOT mutate the returned dict — it is a cached reference.
        Uses double-checked locking for thread-safe lazy loading.
        """
        cache = self._json_cache
        if filepath in cache:
            return cache[filepath]

        with self._lock:
            if filepath in self._json_cache:
                return self._json_cache[filepath]
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._json_cache[filepath] = data
            return data
    
    def _count_packages(self, data: dict) -> int:
        """Count total packages in bundle data."""
        return sum(
            len(section_data['cluster'])
            for section_data in data.values()
            if isinstance(section_data, dict) and 'cluster' in section_data
        )

    def _build_package_data(self, pkg: dict) -> dict:
        """Build a normalized package dict from raw config entry.

        Omits None values and extracts tarball versions from URLs when needed.
        """
        package_data = {
            "package": pkg["package"],
            "type": pkg["type"],
        }
        for key in ("repo_name", "url", "tag", "version"):
            if pkg.get(key) is not None:
                package_data[key] = pkg[key]
        if (
            pkg.get("type") == "tarball"
            and pkg.get("url")
            and not package_data.get("version")
        ):
            extracted = self._extract_version_from_url(pkg["url"])
            if extracted:
                package_data["version"] = extracted
        return package_data

    def _iter_packages(self, data: dict) -> Iterator[tuple[str, dict]]:
        """Yield (section_name, pkg) pairs from loaded bundle data.

        Skips entries missing required 'package' or 'type' keys.
        """
        for section_name, section_data in data.items():
            if not isinstance(section_data, dict) or "cluster" not in section_data:
                continue
            for pkg in section_data["cluster"]:
                if "package" not in pkg or "type" not in pkg:
                    logger.warning("Missing required key(s) in package: %s", pkg)
                    continue
                yield section_name, pkg
    
    def _extract_bundle_name(self, filename_stem: str) -> str:
        """Strip version suffix from a config filename stem.
        
        This uses the same logic as generate_catalog.py for consistency.

        Examples:
            service_k8s_v1.35.1  -> service_k8s
            service_k8s_1.35.1   -> service_k8s
            service_k8s-1.35.1   -> service_k8s
            slurm_custom         -> slurm_custom
        """
        # Try matching a known bundle prefix (pre-sorted for efficiency)
        for name in self._ALL_KNOWN_BUNDLES:
            if filename_stem == name:
                return name
            # version suffixed with _v, _, or -
            if filename_stem.startswith(name) and len(filename_stem) > len(name):
                sep = filename_stem[len(name)]
                if sep in ('_', '-'):
                    remainder = filename_stem[len(name) + 1:]
                    # strip optional leading 'v'
                    if remainder.startswith('v'):
                        remainder = remainder[1:]
                    if remainder and self._VERSION_RE.match(remainder):
                        return name
        # Fallback: try generic regex stripping
        stripped = self._VERSION_SUFFIX_RE.sub('', filename_stem)
        return stripped
    
    def _classify_bundle(self, bundle_name: str) -> str:
        """Classify bundle as functional, infra, or os.
        
        Uses _extract_bundle_name to handle version suffixes.
        """
        # Extract base bundle name (strip version suffix)
        base_name = self._extract_bundle_name(bundle_name)
        
        if base_name in self._FUNCTIONAL_BUNDLES:
            return "functional"
        elif base_name in self._INFRA_BUNDLES:
            return "infrastructure"
        elif base_name in self._OS_BUNDLES:
            return "os"
        else:
            logger.debug("Unknown bundle %r classified as 'os'", bundle_name)
            return "os"
