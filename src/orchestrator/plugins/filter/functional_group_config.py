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
"""Ansible filter plugin for functional group configuration resolution."""

from __future__ import annotations

from typing import Any

try:
    from ansible.module_utils.functional_group_resolver import (
        GroupConfiguration,
        resolve_group,
    )
except ImportError:
    # Fallback for linting when ansible.module_utils is not in path
    import sys
    from pathlib import Path

    ORCHESTRATOR_ROOT = Path(__file__).resolve().parents[2]
    if str(ORCHESTRATOR_ROOT / "plugins/module_utils") not in sys.path:
        sys.path.insert(0, str(ORCHESTRATOR_ROOT / "plugins/module_utils"))
    from functional_group_resolver import (
        GroupConfiguration,
        resolve_group,
    )


def resolve_functional_group_config(
    config_data: dict[str, Any], group: str
) -> dict[str, Any]:
    """Resolve effective configuration for a functional group.

    Args:
        config_data: Parsed functional_group_config.yml data.
        group: Functional group name.

    Returns:
        Dictionary with resolved configuration values.
    """
    resolved = resolve_group(config_data, group)

    return {
        "boot_kernel_params": resolved.boot_kernel_params.value,
        "boot_kernel_params_provenance": resolved.boot_kernel_params.provenance,
        "boot_kernel_params_mode": resolved.boot_kernel_params_mode.value,
        "boot_kernel_params_mode_provenance": resolved.boot_kernel_params_mode.provenance,
        "cloud_init_config_file": resolved.cloud_init_config_file.value,
        "cloud_init_config_file_provenance": resolved.cloud_init_config_file.provenance,
        "image_override": resolved.image_override,
    }


class FilterModule:
    """Ansible filter plugin class."""

    def filters(self) -> dict[str, Any]:
        """Return the filter mapping."""
        return {
            "resolve_functional_group_config": resolve_functional_group_config,
        }
