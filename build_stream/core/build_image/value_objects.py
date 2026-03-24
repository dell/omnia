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

"""Value objects for Build Image domain.

All value objects are immutable and defined by their values, not identity.
"""

import re
from dataclasses import dataclass
from typing import ClassVar, List


@dataclass(frozen=True)
class Architecture:
    """Build image architecture type.

    Attributes:
        value: Architecture name (x86_64 or aarch64).

    Raises:
        ValueError: If architecture is not supported.
    """

    value: str

    SUPPORTED_ARCHITECTURES: ClassVar[List[str]] = ["x86_64", "aarch64"]

    def __post_init__(self) -> None:
        """Validate architecture."""
        if not self.value or not self.value.strip():
            raise ValueError("Architecture cannot be empty")
        if self.value not in self.SUPPORTED_ARCHITECTURES:
            raise ValueError(
                f"Unsupported architecture: {self.value}. "
                f"Supported: {', '.join(self.SUPPORTED_ARCHITECTURES)}"
            )

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    @property
    def is_x86_64(self) -> bool:
        """Check if architecture is x86_64."""
        return self.value == "x86_64"

    @property
    def is_aarch64(self) -> bool:
        """Check if architecture is aarch64."""
        return self.value == "aarch64"


@dataclass(frozen=True)
class ImageKey:
    """Image key identifier for build image.

    Attributes:
        value: Image key string.

    Raises:
        ValueError: If image key format is invalid.
    """

    value: str

    MAX_LENGTH: ClassVar[int] = 128
    KEY_PATTERN: ClassVar[str] = r'^[a-zA-Z0-9_\-]+$'

    def __post_init__(self) -> None:
        """Validate image key format."""
        if not self.value or not self.value.strip():
            raise ValueError("Image key cannot be empty")
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"Image key length cannot exceed {self.MAX_LENGTH} "
                f"characters, got {len(self.value)}"
            )
        if not re.match(self.KEY_PATTERN, self.value):
            raise ValueError(
                f"Invalid image key format: {self.value}. "
                f"Must contain only alphanumeric characters, underscores, and hyphens."
            )

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class FunctionalGroups:
    """Functional groups list for build image.

    Attributes:
        groups: List of functional group names.

    Raises:
        ValueError: If functional groups are invalid.
    """

    groups: List[str]

    MAX_GROUPS: ClassVar[int] = 50
    GROUP_PATTERN: ClassVar[str] = r'^[a-zA-Z0-9_\-]+$'

    def __post_init__(self) -> None:
        """Validate functional groups."""
        if not self.groups:
            raise ValueError("Functional groups cannot be empty")
        if len(self.groups) > self.MAX_GROUPS:
            raise ValueError(
                f"Functional groups cannot exceed {self.MAX_GROUPS} groups, "
                f"got {len(self.groups)}"
            )
        for group in self.groups:
            if not group or not group.strip():
                raise ValueError("Functional group name cannot be empty")
            if not re.match(self.GROUP_PATTERN, group):
                raise ValueError(
                    f"Invalid functional group name: {group}. "
                    f"Must contain only alphanumeric characters, underscores, and hyphens."
                )

    def to_list(self) -> List[str]:
        """Return a copy of the groups list."""
        return list(self.groups)

    def __str__(self) -> str:
        """Return string representation."""
        return str(self.groups)


@dataclass(frozen=True)
class InventoryHost:
    """Inventory host IP address for aarch64 builds.

    Attributes:
        value: IP address or hostname.

    Raises:
        ValueError: If host format is invalid.
    """

    value: str

    MAX_LENGTH: ClassVar[int] = 255
    HOST_PATTERN: ClassVar[str] = r'^[a-zA-Z0-9\.\-]+$'

    def __post_init__(self) -> None:
        """Validate inventory host format."""
        if not self.value or not self.value.strip():
            raise ValueError("Inventory host cannot be empty")
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"Inventory host length cannot exceed {self.MAX_LENGTH} "
                f"characters, got {len(self.value)}"
            )
        if not re.match(self.HOST_PATTERN, self.value):
            raise ValueError(
                f"Invalid inventory host format: {self.value}. "
                f"Must contain only alphanumeric characters, dots, and hyphens."
            )

    def __str__(self) -> str:
        """Return string representation."""
        return self.value
