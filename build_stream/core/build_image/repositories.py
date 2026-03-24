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

"""Repository interfaces for Build Image module."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from core.build_image.value_objects import Architecture, InventoryHost


class BuildStreamConfigRepository(ABC):
    """Repository for reading build stream configuration."""

    @abstractmethod
    def get_aarch64_inv_host(self, job_id: str) -> Optional[InventoryHost]:
        """Get aarch64 inventory host for builds.

        Args:
            job_id: Job identifier.

        Returns:
            Inventory host IP or None if not configured.

        Raises:
            ConfigFileError: If config file cannot be read.
        """
        ...


class BuildImageInventoryRepository(ABC):
    """Repository for creating and managing inventory files for aarch64 builds."""

    @abstractmethod
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
        ...
