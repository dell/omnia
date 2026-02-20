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

"""NFS-based implementation of BuildImageInventoryRepository."""

import logging
from pathlib import Path

from core.build_image.value_objects import InventoryHost

logger = logging.getLogger(__name__)

DEFAULT_INVENTORY_DIR = "/opt/omnia/build_stream_inv"
DEFAULT_INVENTORY_FILENAME = "inv"


class NfsBuildImageInventoryRepository:
    """NFS shared volume implementation for build image inventory file management.

    Creates and manages Ansible inventory files for aarch64 builds.
    """

    def __init__(
        self,
        inventory_dir: str = DEFAULT_INVENTORY_DIR,
        inventory_filename: str = DEFAULT_INVENTORY_FILENAME,
    ) -> None:
        """Initialize repository with inventory directory path.

        Args:
            inventory_dir: Directory path for inventory files.
            inventory_filename: Name of the inventory file.
        """
        self._inventory_dir = Path(inventory_dir)
        self._inventory_filename = inventory_filename

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
        # Ensure inventory directory exists
        try:
            self._inventory_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Failed to create inventory directory %s: %s", self._inventory_dir, exc)
            raise IOError(f"Failed to create inventory directory: {exc}") from exc

        inventory_file_path = self._inventory_dir / self._inventory_filename

        # Create inventory file content
        inventory_content = f"[admin_aarch64]\n{str(inventory_host)}\n"

        try:
            with open(inventory_file_path, "w", encoding="utf-8") as inv_file:
                inv_file.write(inventory_content)

            logger.info(
                "Created inventory file for job %s at %s with host %s",
                job_id,
                inventory_file_path,
                str(inventory_host),
            )
            return inventory_file_path

        except OSError as exc:
            logger.error(
                "Failed to write inventory file %s for job %s: %s",
                inventory_file_path,
                job_id,
                exc,
            )
            raise IOError(f"Failed to write inventory file: {exc}") from exc
