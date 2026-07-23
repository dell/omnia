"""Service for reading software_config.json and extracting role/bundle mappings.

This service loads the software_config.json file and provides methods to:
- List all available roles
- Get bundles associated with a role
- Get allowed bundles per architecture
- Get software versions
"""

import copy
import json
import os
import threading
from collections.abc import Iterator
from typing import Any, Optional

import logging

logger = logging.getLogger(__name__)

# Top-level keys that are not bundle-to-roles mappings.
_NON_BUNDLE_KEYS = frozenset({"bundle_roles", "allowed_bundles", "software_versions"})


class SoftwareConfigService:
    """Service for reading software_config.json and extracting role/bundle mappings."""

    def __init__(self, settings=None, config_dir: Optional[str] = None):
        """Initialize service with settings or config directory path.

        Args:
            settings: Settings instance with base_input_dir path
            config_dir: Direct config directory path (for backward compatibility)

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
            self.config_dir = self.settings.base_input_dir

        self.software_config_path = os.path.join(self.config_dir, 'software_config.json')
        self._config_cache: Optional[dict[str, Any]] = None
        self._lock = threading.Lock()
        logger.debug("SoftwareConfigService initialized with config_dir: %s", self.config_dir)

    def __repr__(self) -> str:
        return f"SoftwareConfigService(config_dir={self.config_dir!r})"

    def reload(self) -> None:
        """Force re-read from disk on the next access.

        Thread-safe: concurrent readers will see either the old
        cached value or wait for a fresh load after invalidation.
        """
        with self._lock:
            self._config_cache = None

    # ------------------------------------------------------------------ #
    #  Internal loader                                                     #
    # ------------------------------------------------------------------ #

    def _load_software_config(self) -> dict[str, Any]:
        """Load and cache software_config.json (EAFP, no TOCTOU).

        Returns cached config. Internal use only — callers MUST NOT mutate.
        """
        cache = self._config_cache
        if cache is not None:
            return cache

        with self._lock:
            cache = self._config_cache
            if cache is not None:
                return cache

            try:
                with open(self.software_config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except FileNotFoundError:
                logger.warning("Config not found: %s", self.software_config_path)
                data = {}
            except json.JSONDecodeError as exc:
                logger.error("Bad JSON in %s: %s", self.software_config_path, exc)
                data = {}
            except OSError as exc:
                logger.error("IO error reading %s: %s", self.software_config_path, exc)
                data = {}
            else:
                if not isinstance(data, dict):
                    logger.error(
                        "Expected JSON object in %s, got %s",
                        self.software_config_path,
                        type(data).__name__,
                    )
                    data = {}

            self._config_cache = data
            return data

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def get_all_roles(self) -> set[str]:
        """Return all role names defined under ``bundle_roles``."""
        config = self._load_software_config()
        return set(config.get("bundle_roles", {}).keys())

    def get_bundles_for_role(self, role: str) -> list[str]:
        """Return bundles associated with a given role (new format only).

        Args:
            role: The role name to look up.

        Returns:
            List of bundle names, or empty list if role not found.
        """
        config = self._load_software_config()
        return list(config.get("bundle_roles", {}).get(role, []))

    def get_role_bundles(self, role: str) -> list[str]:
        """Get bundles associated with a specific role (legacy + new format).

        Args:
            role: Role name (e.g., 'slurm_control_node')

        Returns:
            List of bundle names associated with the role
        """
        config = self._load_software_config()
        bundles: set[str] = set()

        # New format: bundle_roles mapping
        if "bundle_roles" in config:
            bundles.update(config["bundle_roles"].get(role, []))

        # Legacy format: top-level key is a bundle named after the role
        if role in config and isinstance(config[role], list):
            bundles.add(role)

        # Legacy format: role appears in bundle's role list
        for key, value in config.items():
            if key in _NON_BUNDLE_KEYS:
                continue
            if isinstance(value, list):
                for r in value:
                    if isinstance(r, str) and r == role:
                        bundles.add(key)
                    elif isinstance(r, dict) and r.get("name") == role:
                        bundles.add(key)

        return sorted(list(bundles))

    def get_allowed_bundles(
        self, architecture: Optional[str] = None,
    ) -> dict[str, list[str]]:
        """Return allowed bundles, optionally filtered by architecture.

        Args:
            architecture: If provided, return only bundles for this arch.

        Returns:
            Dict mapping architecture names to lists of bundle names.
        """
        config = self._load_software_config()
        allowed = config.get("allowed_bundles", {})
        if architecture is not None:
            return {architecture: list(allowed.get(architecture, []))}
        return {k: list(v) for k, v in allowed.items()}

    def get_software_versions(self) -> dict[str, str]:
        """Return software version mappings."""
        config = self._load_software_config()
        return dict(config.get("software_versions", {}))

    def get_bundle_metadata(self, bundle_name: str) -> dict[str, Any]:
        """Return version and architecture metadata for a software bundle.

        Args:
            bundle_name: The bundle name to look up.

        Returns:
            Dict with 'version' and 'arch' keys (empty if not found).
        """
        config = self._load_software_config()
        if 'softwares' in config:
            for software in config['softwares']:
                if software.get('name') == bundle_name:
                    return {
                        'version': software.get('version', ''),
                        'arch': software.get('arch', [])
                    }
        return {'version': '', 'arch': []}

    def get_bundle_mappings(self) -> dict[str, Any]:
        """Return top-level entries that are bundle-to-role mappings.

        Excludes known non-bundle keys: ``bundle_roles``,
        ``allowed_bundles``, ``software_versions``.
        """
        config = self._load_software_config()
        return {
            k: copy.deepcopy(v)
            for k, v in config.items()
            if k not in _NON_BUNDLE_KEYS
        }

    def iter_role_bundle_pairs(self) -> Iterator[tuple[str, str]]:
        """Yield ``(role, bundle)`` pairs from ``bundle_roles``."""
        config = self._load_software_config()
        for role, bundles in config.get("bundle_roles", {}).items():
            for bundle in bundles:
                yield role, bundle