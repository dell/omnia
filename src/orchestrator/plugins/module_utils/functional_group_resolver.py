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
"""Functional group configuration resolver.

This module resolves effective configuration for a functional group by
applying the precedence order: exact-group scope, common scope, Omnia default.
It also tracks provenance for each resolved value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResolvedValue:
    """A resolved configuration value with provenance tracking."""

    value: Any
    provenance: str = field(default="default")

    def __bool__(self) -> bool:
        """Return whether the value is non-empty."""
        if isinstance(self.value, str):
            return bool(self.value.strip())
        return bool(self.value)


@dataclass
class GroupConfiguration:
    """Resolved configuration for a single functional group."""

    boot_kernel_params: ResolvedValue = field(default_factory=lambda: ResolvedValue(""))
    boot_kernel_params_mode: ResolvedValue = field(
        default_factory=lambda: ResolvedValue("append")
    )
    cloud_init_config_file: ResolvedValue = field(
        default_factory=lambda: ResolvedValue("")
    )
    image_override: dict[str, Any] = field(default_factory=dict)


def _resolve_field(
    config_data: dict[str, Any],
    group: str,
    field_path: list[str],
    default: Any,
) -> tuple[Any, str]:
    """Resolve a field using precedence: exact-group, common, default.

    Args:
        config_data: Parsed functional_group_config.yml data.
        group: Functional group name.
        field_path: List of keys to traverse (e.g., ["boot_kernel_params"]).
        default: Omnia default value.

    Returns:
        Tuple of (resolved_value, provenance).
    """
    # Check exact-group scope
    groups = config_data.get("groups", {})
    if isinstance(groups, dict) and group in groups:
        group_scope = groups[group]
        if isinstance(group_scope, dict):
            value = group_scope
            for key in field_path:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            if _is_non_empty(value):
                return value, f"groups.{group}." + ".".join(field_path)

    # Check common scope
    common = config_data.get("common")
    if isinstance(common, dict):
        value = common
        for key in field_path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                value = None
                break
        if _is_non_empty(value):
            return value, "common." + ".".join(field_path)

    # Use default
    return default, "default"


def _is_non_empty(value: Any) -> bool:
    """Return whether a value is non-empty."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def resolve_group(config_data: dict[str, Any], group: str) -> GroupConfiguration:
    """Resolve effective configuration for a functional group.

    Args:
        config_data: Parsed functional_group_config.yml data.
        group: Functional group name.

    Returns:
        GroupConfiguration with resolved values and provenance.
    """
    # Resolve boot_kernel_params
    boot_kernel_params_value, boot_kernel_params_provenance = _resolve_field(
        config_data, group, ["boot_kernel_params"], ""
    )

    # Resolve boot_kernel_params_mode
    boot_kernel_params_mode_value, boot_kernel_params_mode_provenance = _resolve_field(
        config_data, group, ["boot_kernel_params_mode"], "append"
    )

    # Resolve cloud_init.config_file
    cloud_init_config_file_value, cloud_init_config_file_provenance = _resolve_field(
        config_data, group, ["cloud_init", "config_file"], ""
    )

    # Resolve image_override (exact-group only)
    image_override = {}
    groups = config_data.get("groups", {})
    if isinstance(groups, dict) and group in groups:
        group_scope = groups[group]
        if isinstance(group_scope, dict):
            override = group_scope.get("image_override")
            if isinstance(override, dict) and override:
                image_override = override

    return GroupConfiguration(
        boot_kernel_params=ResolvedValue(
            boot_kernel_params_value, boot_kernel_params_provenance
        ),
        boot_kernel_params_mode=ResolvedValue(
            boot_kernel_params_mode_value, boot_kernel_params_mode_provenance
        ),
        cloud_init_config_file=ResolvedValue(
            cloud_init_config_file_value, cloud_init_config_file_provenance
        ),
        image_override=image_override,
    )
