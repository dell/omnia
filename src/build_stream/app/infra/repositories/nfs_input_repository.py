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

"""Consolidated NFS-based implementation for input directory and configuration management."""

from api.logging_utils import log_secure_info
import os
from pathlib import Path
from typing import Optional

import yaml

from common.config import load_config
from core.build_image.repositories import (
    BuildStreamConfigRepository,
    BuildImageInventoryRepository,
)
from core.build_image.value_objects import InventoryHost


# Load configuration to get base path
try:
    local_config = load_config()
    DEFAULT_BUILD_STREAM_BASE = Path(local_config.file_store.base_path)
except (FileNotFoundError, AttributeError):
    # Fallback to default path if config is not available
    DEFAULT_BUILD_STREAM_BASE = Path(os.getenv("OMNIA_DATA_PATH", "/opt/omnia")) / "build_stream_root"

def _get_omnia_data_path() -> str:
    """Read OMNIA_DATA_PATH from environment (sourced from omnia.env).

    Returns:
        OMNIA_DATA_PATH value, defaults to '/opt/omnia'.
    """
    return os.environ.get("OMNIA_DATA_PATH", "/opt/omnia")


def _get_omnia_project_name() -> str:
    """Read OMNIA_PROJECT_NAME from environment (sourced from omnia.env).

    Returns:
        OMNIA_PROJECT_NAME value, defaults to 'project_default'.
    """
    return os.environ.get("OMNIA_PROJECT_NAME", "project_default")


def _build_repo_manager_input_dir() -> str:
    """Construct the repo_manager domain input directory path.

    Path: <OMNIA_DATA_PATH>/repo_manager/input/<OMNIA_PROJECT_NAME>/
    """
    return f"{_get_omnia_data_path()}/repo_manager/input/{_get_omnia_project_name()}/"


DEFAULT_PLAYBOOK_INPUT_DIR = _build_repo_manager_input_dir()


class NfsInputRepository(BuildStreamConfigRepository, BuildImageInventoryRepository):
    """Consolidated NFS repository for input directory and configuration management.

    This repository combines functionality for:
    - Input directory path management
    - Configuration file reading
    - Inventory file creation

    With domain segregation (Omnia 2.3+), input paths are constructed from
    OMNIA_DATA_PATH and OMNIA_PROJECT_NAME environment variables (sourced
    from omnia.env) rather than from a monolithic /opt/omnia/input/ directory.
    """

    def __init__(
        self,
        config_file_path: Optional[str] = None,
        playbook_input_dir: str = DEFAULT_PLAYBOOK_INPUT_DIR,
        build_stream_base: str = DEFAULT_BUILD_STREAM_BASE,
        inventory_base_dir: str = None,
    ):
        """Initialize repository with consolidated paths.

        Args:
            config_file_path: Full path to build_stream_config.yml.  If None,
                             constructed from OMNIA_DATA_PATH / OMNIA_PROJECT_NAME.
            playbook_input_dir: Destination path for image_build_manager domain input.
            build_stream_base: Base path for build stream job data.
            inventory_base_dir: Base directory for inventory files.
        """
        # Initialize configuration paths
        if config_file_path is None:
            data_path = _get_omnia_data_path()
            project = _get_omnia_project_name()
            config_file_path = (
                f"{data_path}/build_stream/input/{project}/build_stream_config.yml"
            )
        self._config_file_path = Path(config_file_path)

        # Initialize input directory paths
        self._playbook_input_dir = Path(playbook_input_dir)
        self._build_stream_base = Path(build_stream_base)

        # Initialize inventory directory paths
        if inventory_base_dir is None:
            inventory_base_dir = os.path.join(_get_omnia_data_path(), "build_stream_inv")
        self._inventory_base_dir = Path(inventory_base_dir)

    # === Configuration Methods ===

    def get_aarch64_inv_host(self, job_id: str) -> Optional[InventoryHost]:
        """Retrieve aarch64 inventory host IP from build_stream_config.yml.

        Args:
            job_id: Job identifier.

        Returns:
            Inventory host IP address or None if not configured.

        Raises:
            ConfigurationError: If config file is invalid or inaccessible.
        """
        config_path = self._config_file_path

        if not config_path.exists():
            log_secure_info('warning', f"build_stream_config.yml not found at {job_id} (job {config_path})")
            return None

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                
            if not config:
                log_secure_info('warning', f"Empty build_stream_config.yml for job {job_id}")
                return None
                
            inventory_host = config.get("aarch64_inventory_host_ip")
            if inventory_host:
                log_secure_info('info', f"Retrieved inventory_host for job {job_id}: {inventory_host}")
                return InventoryHost(str(inventory_host))
            
            log_secure_info('info', f"No aarch64_inventory_host_ip configured for job {job_id}")
            return None
            
        except yaml.YAMLError as exc:
            log_secure_info('error', f"Failed to parse build_stream_config.yml for job {job_id}")
            return None
        except Exception as exc:
            log_secure_info('error', f"Unexpected error reading build_stream_config.yml for job {job_id}")
            return None

    # === Inventory File Methods ===

    def create_inventory_file(self, inventory_host: InventoryHost, job_id: str) -> Path:
        """Create an inventory file for aarch64 builds.

        Args:
            inventory_host: The inventory host IP address.
            job_id: Job identifier for tracking.

        Returns:
            Path to the created inventory file.

        Raises:
            IOError: If inventory file cannot be created.
        """
        try:
            # Create inventory directory if it doesn't exist
            inventory_dir = self._inventory_base_dir / job_id
            inventory_dir.mkdir(parents=True, exist_ok=True)

            # Create inventory file path
            inventory_file = inventory_dir / "inv"

            # Create inventory content
            inventory_content = f"[admin_aarch64]\n{inventory_host.value}\n"

            # Write inventory file
            with open(inventory_file, "w", encoding="utf-8") as f:
                f.write(inventory_content)

            log_secure_info('info', f"Created inventory file for job {job_id} at {inventory_file} with host {inventory_host.value}")

            return inventory_file

        except (OSError, IOError) as exc:
            log_secure_info('error', f"Failed to create inventory file for job {job_id}")
            raise IOError("Cannot create inventory file") from None

    # === Input Directory Management Methods ===

    def get_source_input_repository_path(self, job_id: str) -> Path:
        """Get source input directory path for a job.

        Args:
            job_id: Job identifier.

        Returns:
            Path like <omnia/build_stream_root>/artifacts/{job_id}/input/
        """
        return self._build_stream_base / job_id / "input"

    def get_destination_input_repository_path(self) -> Path:
        """Get destination input directory path expected by playbook.

        Returns:
            Path like /opt/omnia/input/project_default/
        """
        return self._playbook_input_dir

    def validate_input_directory(self, path: Path) -> bool:
        """Validate that input directory exists and contains required files.

        Args:
            path: Path to the input directory to validate.

        Returns:
            True if directory is valid and contains at least one file.
        """
        if not path.is_dir():
            log_secure_info('warning', f"Input directory does not exist: {path}")
            return False

        has_files = any(path.iterdir())
        if not has_files:
            log_secure_info('warning', f"Input directory is empty: {path}")
            return False

        return True
