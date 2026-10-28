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

from core.build_image.repositories import BuildStreamConfigRepository
from core.build_image.value_objects import InventoryHost


def _get_omnia_data_path() -> str:
    """Read OMNIA_DATA_PATH from environment (sourced from omnia.env).

    Returns:
        OMNIA_DATA_PATH value, defaults to '/opt/omnia'.
    """
    return os.environ.get("OMNIA_DATA_PATH", "/opt/omnia")


def _get_omnia_project_name() -> str:
    """Read OMNIA_PROJECT_NAME from environment (sourced from omnia.env).

    Validates the value is a single safe path segment to prevent
    path-traversal via crafted environment values.

    Returns:
        OMNIA_PROJECT_NAME value, defaults to 'project_default'.

    Raises:
        ValueError: If the project name contains path separators or
            traversal components.
    """
    import re  # local import to avoid module-level side effects
    project_name = os.environ.get("OMNIA_PROJECT_NAME", "project_default")
    if (
        not project_name
        or project_name in ('.', '..')
        or os.path.basename(project_name) != project_name
        or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,254}', project_name)
    ):
        raise ValueError("OMNIA_PROJECT_NAME is not a valid single-segment name")
    return project_name


def _build_repo_manager_input_dir() -> str:
    """Construct the repo_manager domain input directory path.

    Path: <OMNIA_DATA_PATH>/repo_manager/input/<OMNIA_PROJECT_NAME>/
    """
    return f"{_get_omnia_data_path()}/repo_manager/input/{_get_omnia_project_name()}/"


DEFAULT_PLAYBOOK_INPUT_DIR = _build_repo_manager_input_dir()


class NfsInputRepository(BuildStreamConfigRepository):
    """Consolidated NFS repository for input directory and configuration management.

    This repository combines functionality for:
    - Input directory path management
    - Configuration file reading

    With domain segregation (Omnia 2.3+), input paths are constructed from
    OMNIA_DATA_PATH and OMNIA_PROJECT_NAME environment variables (sourced
    from omnia.env) rather than from a monolithic /opt/omnia/input/ directory.
    """

    def __init__(
        self,
        config_file_path: Optional[str] = None,
        playbook_input_dir: str = DEFAULT_PLAYBOOK_INPUT_DIR,
    ):
        """Initialize repository with consolidated paths.

        Args:
            config_file_path: Full path to build_stream_config.yml.  If None,
                             constructed from OMNIA_DATA_PATH / OMNIA_PROJECT_NAME.
            playbook_input_dir: Destination path for image_build_manager domain input.
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

    # === Input Directory Management Methods ===

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
