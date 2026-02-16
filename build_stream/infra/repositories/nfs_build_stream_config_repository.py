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

"""NFS-based implementation of BuildImageConfigRepository."""

import logging
import os
from pathlib import Path
from typing import Optional

import yaml

from core.build_image.repositories import BuildImageConfigRepository

logger = logging.getLogger(__name__)


def _read_project_name(default_file_path: str = "/opt/omnia/input/default.yml") -> str:
    """Read project_name from default.yml.

    Args:
        default_file_path: Path to default.yml file.

    Returns:
        Project name (e.g., "project_default"). Returns 'project_default' fallback on any error.
    """
    default_path = Path(default_file_path)
    if not default_path.exists():
        return "project_default"

    try:
        with open(default_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if not config or "project_name" not in config:
            return "project_default"
        return str(config["project_name"])
    except yaml.YAMLError:
        return "project_default"
    except Exception:
        return "project_default"


class NfsBuildStreamConfigRepository(BuildImageConfigRepository):
    """Repository for build_stream_config.yml access."""

    def __init__(
        self,
        config_file_path: Optional[str] = None,
        default_file_path: str = "/opt/omnia/input/default.yml",
    ):
        """Initialize repository with shared config path.

        Args:
            config_file_path: Full path to build_stream_config.yml. If None, constructed
                             using project_name from default.yml.
            default_file_path: Path to default.yml to read project_name.
        """
        if config_file_path is None:
            project_name = _read_project_name(default_file_path)
            config_file_path = f"/opt/omnia/input/{project_name}/build_stream_config.yml"
        self._config_file_path = Path(config_file_path)

    def get_inventory_host(self, job_id: str) -> Optional[str]:
        """Retrieve inventory host IP from build_stream_config.yml.

        Args:
            job_id: Job identifier.

        Returns:
            Inventory host IP address or None if not configured.

        Raises:
            ConfigurationError: If config file is invalid or inaccessible.
        """
        config_path = self._config_file_path

        if not config_path.exists():
            logger.warning(
                "build_stream_config.yml not found at %s (job %s)",
                job_id,
                config_path,
            )
            return None

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                
            if not config:
                logger.warning("Empty build_stream_config.yml for job %s", job_id)
                return None
                
            inventory_host = config.get("aarch64_inventory_host")
            if inventory_host:
                logger.info(
                    "Retrieved inventory_host for job %s: %s",
                    job_id,
                    inventory_host,
                )
                return str(inventory_host)
            
            logger.info("No aarch64_inventory_host configured for job %s", job_id)
            return None
            
        except yaml.YAMLError as exc:
            logger.error(
                "Failed to parse build_stream_config.yml for job %s: %s",
                job_id,
                exc,
            )
            return None
        except Exception as exc:
            logger.error(
                "Unexpected error reading build_stream_config.yml for job %s: %s",
                job_id,
                exc,
            )
            return None
