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
"""Resolve per-functional-group boot and cloud-init configuration.

Single source of precedence for ``functional_group_config.yml``. Both the
provisioning path and the configuration-only publication path consume this
module so the two cannot drift apart.

Precedence for every value::

    groups.<exact-name>  ->  common  ->  Omnia default

An empty value (``""`` or ``[]``) means "inherit from the next level down".
It does not mean "set to empty"; this release provides no clearing sentinel.
"""

from __future__ import annotations

import re
from typing import Any, NamedTuple

#: Source levels recorded as provenance, most specific first.
LEVEL_GROUP = "group"
LEVEL_COMMON = "common"
LEVEL_LEGACY = "legacy"
LEVEL_DEFAULT = "default"

#: Built-in defaults, equivalent to standard Slurm-node behavior.
OMNIA_DEFAULTS: dict[str, Any] = {
    "cloud_init_config_file": "",
    "image_override": {},
}

#: Artifact references an ``image_override`` must supply together.
IMAGE_OVERRIDE_KEYS = ("kernel", "initrd", "rootfs")

#: The runtime PXE mapping renames the first control-plane node's group with a
#: ``_first`` marker. Operators configure the canonical mapping name, so the
#: marker is removed before the group lookup.
_FIRST_CONTROL_PLANE = re.compile(r"^service_kube_control_plane_first_")

#: ``image_override`` is group-only: ``common`` cannot set it, because an image
#: applies to one group's hardware and architecture rather than to a cluster.
_GROUP_ONLY_KEYS = ("image_override",)


class ResolvedValue(NamedTuple):
    """One resolved setting and the level that supplied it."""

    value: Any
    source: str


class ResolvedGroupConfig(NamedTuple):
    """Fully resolved configuration for a single functional group."""

    functional_group: str
    cloud_init_config_file: ResolvedValue
    image_override: ResolvedValue

    def provenance(self) -> dict[str, str]:
        """Return a ``{setting: level}`` map for current-run evidence."""
        return {
            "cloud_init_config_file": self.cloud_init_config_file.source,
            "image_override": self.image_override.source,
        }

    def values(self) -> dict[str, Any]:
        """Return a ``{setting: value}`` map for template consumption."""
        return {
            "cloud_init_config_file": self.cloud_init_config_file.value,
            "image_override": self.image_override.value,
        }


def _is_inherit(value: Any) -> bool:
    """Return whether a value means "inherit from the next level down".

    An absent key, ``None``, an empty/whitespace string, and an empty list all
    inherit. A populated value of any kind overrides.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


def _scope(config_data: Any, key: str) -> dict[str, Any]:
    """Return a top-level scope mapping, tolerating absent or malformed input."""
    if not isinstance(config_data, dict):
        return {}
    scope = config_data.get(key)
    return scope if isinstance(scope, dict) else {}


def canonical_group_name(functional_group: str) -> str:
    """Return the operator-facing name for a runtime functional-group name."""
    return _FIRST_CONTROL_PLANE.sub(
        "service_kube_control_plane_", str(functional_group)
    )


def _group_scope(config_data: Any, functional_group: str) -> dict[str, Any]:
    """Return the exact-name group scope, or an empty mapping."""
    groups = _scope(config_data, "groups")
    scope = groups.get(canonical_group_name(functional_group))
    return scope if isinstance(scope, dict) else {}


def _cloud_init_file(scope: dict[str, Any]) -> Any:
    """Return a scope's cloud-init ``config_file``, or ``None``."""
    cloud_init = scope.get("cloud_init")
    if not isinstance(cloud_init, dict):
        return None
    return cloud_init.get("config_file")


def _resolve(
    candidates: list[tuple[str, Any]], default: Any
) -> ResolvedValue:
    """Return the first non-inheriting candidate, else the Omnia default."""
    for level, value in candidates:
        if not _is_inherit(value):
            return ResolvedValue(value, level)
    return ResolvedValue(default, LEVEL_DEFAULT)


def resolve_group(
    config_data: Any,
    functional_group: str,
) -> ResolvedGroupConfig:
    """Resolve the effective configuration for one functional group.

    Args:
        config_data: Parsed ``functional_group_config.yml``, or ``None`` when
            the optional file is absent.
        functional_group: Exact PXE functional-group name.

    Returns:
        The resolved configuration with per-setting provenance.
    """
    group = _group_scope(config_data, functional_group)
    common = _scope(config_data, "common")

    resolved: dict[str, ResolvedValue] = {}

    resolved["cloud_init_config_file"] = _resolve(
        [
            (LEVEL_GROUP, _cloud_init_file(group)),
            (LEVEL_COMMON, _cloud_init_file(common)),
        ],
        OMNIA_DEFAULTS["cloud_init_config_file"],
    )

    for key in _GROUP_ONLY_KEYS:
        resolved[key] = _resolve(
            [(LEVEL_GROUP, group.get(key))], OMNIA_DEFAULTS[key]
        )

    return ResolvedGroupConfig(
        functional_group=functional_group,
        cloud_init_config_file=resolved["cloud_init_config_file"],
        image_override=resolved["image_override"],
    )


def resolve_all(
    config_data: Any,
    functional_groups: list[str],
) -> dict[str, ResolvedGroupConfig]:
    """Resolve every named functional group.

    Args:
        config_data: Parsed ``functional_group_config.yml``, or ``None``.
        functional_groups: Exact PXE functional-group names to resolve.

    Returns:
        Mapping of functional-group name to its resolved configuration.
    """
    return {
        name: resolve_group(config_data, name)
        for name in functional_groups
    }


def configured_group_names(config_data: Any) -> list[str]:
    """Return the group names this file declares, in declaration order."""
    return list(_scope(config_data, "groups").keys())


def has_effective_configuration(config_data: Any) -> bool:
    """Return whether the input declares any non-inheriting value.

    The shipped template contains empty ``common`` and ``groups`` scopes. Its
    mere presence must not disable the legacy additional-cloud-init path; only
    an effective new value makes the two contracts mutually exclusive.
    """
    if not isinstance(config_data, dict):
        return False

    def _scope_is_active(scope: Any) -> bool:
        if not isinstance(scope, dict):
            return False
        for key, value in scope.items():
            if key == "cloud_init" and isinstance(value, dict):
                if not _is_inherit(value.get("config_file")):
                    return True
            elif not _is_inherit(value):
                return True
        return False

    if _scope_is_active(config_data.get("common")):
        return True
    groups = config_data.get("groups")
    return isinstance(groups, dict) and any(
        _scope_is_active(scope) for scope in groups.values()
    )


def configured_group_names(config_data: Any) -> list[str]:
