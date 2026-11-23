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
        """Return simplified source name (group, common, default)."""
        if "groups." in self.provenance:
            return "group"
        if "common" in self.provenance:
            return "common"
        return self.provenance

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, tuple) and len(other) == 2:
            return other in ((self.value, self.source), (self.value, self.provenance))
        if isinstance(other, ResolvedValue):
            return self.value == other.value and self.provenance == other.provenance
        return self.value == other

    def __bool__(self) -> bool:
        """Return whether the value is non-empty."""
        if isinstance(self.value, str):
            return bool(self.value.strip())
        return bool(self.value)

    def __getitem__(self, key: Any) -> Any:
        return self.value[key]

    def get(self, key: Any, default: Any = None) -> Any:
        """Get an item from the underlying mapping value."""
        if isinstance(self.value, dict):
            return self.value.get(key, default)
        return default

    def __contains__(self, key: Any) -> bool:
        return key in self.value if isinstance(self.value, (dict, list, str)) else False

    def keys(self):
        """Return mapping keys of the underlying value."""
        return self.value.keys() if isinstance(self.value, dict) else {}.keys()

    def values(self):
        """Return mapping values of the underlying value."""
        return self.value.values() if isinstance(self.value, dict) else {}.values()

    def items(self):
        """Return mapping items of the underlying value."""
        return self.value.items() if isinstance(self.value, dict) else {}.items()


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
    """Map runtime group alias (e.g. _control_plane_first_) to canonical group name."""
    if "_control_plane_first_" in group:
        return group.replace("_control_plane_first_", "_control_plane_")
    return group


def merge_cloud_init_sections(
    base: dict[str, Any], posts: list[dict[str, Any]]
) -> dict[str, Any]:
    """Merge base cloud-init with ordered post-configuration sections without mutating base."""
    merged = copy.deepcopy(base)
    for post in posts:
        for section, content in post.items():
            if section not in merged:
                merged[section] = copy.deepcopy(content)
            elif isinstance(merged[section], list) and isinstance(content, list):
                merged[section] = list(merged[section]) + copy.deepcopy(content)
            elif isinstance(merged[section], dict) and isinstance(content, dict):
                merged[section] = {**merged[section], **copy.deepcopy(content)}
            else:
                merged[section] = copy.deepcopy(content)
    return merged


def has_effective_configuration(template: dict[str, Any] | None) -> bool:
    """Return True if template contains any active flexible-group configuration."""
    if not template or not isinstance(template, dict):
        return False

    def _scope_active(scope: Any) -> bool:
        if not isinstance(scope, dict):
            return False
        if _is_non_empty(scope.get("boot_kernel_params")):
            return True
        ci = scope.get("cloud_init")
        if isinstance(ci, dict) and _is_non_empty(ci.get("config_file")):
            return True
        if _is_non_empty(scope.get("image_override")):
            return True
        return False

    if _scope_active(template.get("common")):
        return True
    groups = template.get("groups")
    if isinstance(groups, dict):
        for g_data in groups.values():
            if _scope_active(g_data):
                return True
    return False


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
    canon_group = canonical_group_name(group)
    lookup_group = group if (isinstance(groups, dict) and group in groups) else canon_group
    if isinstance(groups, dict) and lookup_group in groups:
        group_scope = groups[lookup_group]
        if isinstance(group_scope, dict):
            value = group_scope
            for key in field_path:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            if _is_non_empty(value):
                return value, f"groups.{lookup_group}." + ".".join(field_path)

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
    image_override_prov = "default"
    groups = config_data.get("groups", {})
    canon_group = canonical_group_name(group)
    lookup_group = group if (isinstance(groups, dict) and group in groups) else canon_group
    if isinstance(groups, dict) and lookup_group in groups:
        group_scope = groups[lookup_group]
        if isinstance(group_scope, dict):
            override = group_scope.get("image_override")
            if isinstance(override, dict) and override:
                image_override = override
                image_override_prov = f"groups.{lookup_group}.image_override"

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
        image_override=ResolvedValue(image_override, image_override_prov),
    )
