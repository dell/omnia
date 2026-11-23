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

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResolvedValue:
    """A resolved configuration value with provenance tracking."""

    value: Any
    provenance: str = field(default="default")

    @property
    def source(self) -> str:
        """Return the top-level source of this resolved value."""
        return self.provenance.split(".", maxsplit=1)[0]

    def __bool__(self) -> bool:
        """Return whether the value is non-empty."""
        if isinstance(self.value, str):
            return bool(self.value.strip())
        return bool(self.value)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, tuple) and len(other) == 2:
            val, prov = other
            if prov == "group":
                prov_match = self.provenance.startswith("groups.")
            else:
                prov_match = self.provenance == prov or self.provenance.startswith(f"{prov}.")
            return self.value == val and prov_match
        if isinstance(other, ResolvedValue):
            return self.value == other.value and self.provenance == other.provenance
        return self.value == other


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
    image_override: ResolvedValue = field(
        default_factory=lambda: ResolvedValue({}, "default")
    )


def canonical_group_name(group: str) -> str:
    """Return the canonical group name for runtime variants (e.g. _first)."""
    if "service_kube_control_plane_first" in group:
        return group.replace("service_kube_control_plane_first", "service_kube_control_plane")
    return group


def merge_cloud_init_sections(
    base: dict[str, Any], posts: list[dict[str, Any]]
) -> dict[str, Any]:
    """Merge base cloud-init and ordered post-boot sections without mutating inputs."""
    merged = copy.deepcopy(base)
    for post in posts:
        for k, v in post.items():
            if k in merged and isinstance(merged[k], list) and isinstance(v, list):
                merged[k] = merged[k] + copy.deepcopy(v)
            else:
                merged[k] = copy.deepcopy(v)
    return merged


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
    groups = config_data.get("groups", {})
    target_group = group
    if isinstance(groups, dict) and target_group not in groups:
        candidate = canonical_group_name(group)
        if candidate in groups:
            target_group = candidate

    # Check exact-group scope
    if isinstance(groups, dict) and target_group in groups:
        group_scope = groups[target_group]
        if isinstance(group_scope, dict):
            value = group_scope
            for key in field_path:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            if _is_non_empty(value):
                return value, f"groups.{target_group}." + ".".join(field_path)

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
    image_override_val = {}
    image_override_prov = "default"
    groups = config_data.get("groups", {})
    target_group = (
        group if (isinstance(groups, dict) and group in groups)
        else canonical_group_name(group)
    )
    if isinstance(groups, dict) and target_group in groups:
        group_scope = groups[target_group]
        if isinstance(group_scope, dict):
            override = group_scope.get("image_override")
            if isinstance(override, dict) and override:
                image_override_val = override
                image_override_prov = f"groups.{target_group}.image_override"

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
        image_override=ResolvedValue(image_override_val, image_override_prov),
    )
