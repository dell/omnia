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

"""Value objects for Local Repository domain.

All value objects are immutable and defined by their values, not identity.
"""

import re
from dataclasses import dataclass
from typing import ClassVar, Dict, Any


@dataclass(frozen=True)
class PlaybookPath:
    """Validated playbook name for Ansible execution.

    Attributes:
        value: Playbook name (e.g., 'include_input_dir.yml') without path.
              The watcher service will map this to the full path internally.

    Raises:
        ValueError: If name is empty, invalid format, or contains traversal.
    """

    value: str

    MAX_LENGTH: ClassVar[int] = 128  # Reasonable limit for a filename
    ALLOWED_NAME_PATTERN: ClassVar[str] = r'^[a-zA-Z0-9_\-\.]+\.ya?ml$'

    def __post_init__(self) -> None:
        """Validate playbook name format and security."""
        if not self.value or not self.value.strip():
            raise ValueError("Playbook name cannot be empty")
            
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"Playbook name length cannot exceed {self.MAX_LENGTH} "
                f"characters, got {len(self.value)}"
            )
            
        if ".." in self.value:
            raise ValueError(
                f"Path traversal not allowed in playbook name: {self.value}"
            )
            
        if '/' in self.value:
            raise ValueError(
                f"Playbook name cannot contain path separators: {self.value}"
            )

        # Validate playbook name format
        if not re.match(self.ALLOWED_NAME_PATTERN, self.value):
            raise ValueError(
                f"Invalid playbook name format: {self.value}. "
                f"Must be a valid filename with .yml or .yaml extension."
            )

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class ExtraVars:
    """Ansible extra variables container.

    Immutable container for ansible-playbook --extra-vars parameters.

    Attributes:
        values: Dictionary of extra variable key-value pairs.

    Raises:
        ValueError: If values is None or contains invalid keys.
    """

    values: Dict[str, Any]

    MAX_KEYS: ClassVar[int] = 50
    KEY_PATTERN: ClassVar[str] = r'^[a-zA-Z_][a-zA-Z0-9_]*$'

    def __post_init__(self) -> None:
        """Validate extra vars structure."""
        if self.values is None:
            raise ValueError("Extra vars cannot be None")
        if len(self.values) > self.MAX_KEYS:
            raise ValueError(
                f"Extra vars cannot exceed {self.MAX_KEYS} keys, "
                f"got {len(self.values)}"
            )
        for key in self.values:
            if not re.match(self.KEY_PATTERN, key):
                raise ValueError(
                    f"Invalid extra var key: {key}. "
                    f"Must match pattern: {self.KEY_PATTERN}"
                )

    def to_dict(self) -> Dict[str, Any]:
        """Return a copy of the extra vars dictionary."""
        return dict(self.values)

    def __str__(self) -> str:
        """Return string representation."""
        return str(self.values)


@dataclass(frozen=True)
class ExecutionTimeout:
    """Timeout configuration for playbook execution.

    Attributes:
        minutes: Timeout duration in minutes.

    Raises:
        ValueError: If minutes is not within valid range.
    """

    minutes: int

    MIN_MINUTES: ClassVar[int] = 1
    MAX_MINUTES: ClassVar[int] = 120
    DEFAULT_MINUTES: ClassVar[int] = 30

    def __post_init__(self) -> None:
        """Validate timeout range."""
        if not isinstance(self.minutes, int):
            raise ValueError(
                f"Timeout minutes must be an integer, got {type(self.minutes)}"
            )
        if self.minutes < self.MIN_MINUTES or self.minutes > self.MAX_MINUTES:
            raise ValueError(
                f"Timeout must be between {self.MIN_MINUTES} and "
                f"{self.MAX_MINUTES} minutes, got {self.minutes}"
            )

    @classmethod
    def default(cls) -> "ExecutionTimeout":
        """Create default timeout configuration."""
        return cls(minutes=cls.DEFAULT_MINUTES)

    def to_seconds(self) -> int:
        """Convert timeout to seconds."""
        return self.minutes * 60

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.minutes}m"
