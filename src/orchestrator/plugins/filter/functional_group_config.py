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
"""Jinja filters exposing the functional-group configuration resolver.

Playbooks must not reimplement the precedence rules in Jinja. These filters
delegate to ``module_utils/functional_group_resolver.py`` so the provisioning
path and the configuration-only publication path resolve identically.
"""

from __future__ import annotations

import importlib.util
import os
from typing import Any

from ansible.errors import AnsibleFilterError

try:  # Installed collection, or a run where module_utils is importable.
    from ansible.module_utils.functional_group_resolver import resolve_group
    from ansible.module_utils.functional_group_resolver import (
        canonical_group_name,
        merge_cloud_init_sections,
    )
except ImportError:  # pragma: no cover - exercised by the repo-layout run
    # Filter plugins execute on the controller, where the `module_utils`
    # setting in ansible.cfg does not apply: that path is for modules shipped
    # to a target. Load the resolver directly from the sibling module_utils
    # directory so the repository layout behaves like an installed collection.
    _RESOLVER_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "module_utils",
        "functional_group_resolver.py",
    )
    _SPEC = importlib.util.spec_from_file_location(
        "omnia_functional_group_resolver", _RESOLVER_PATH
    )
    if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
        raise ImportError(
            f"Cannot load functional group resolver from {_RESOLVER_PATH}"
        ) from None
    _RESOLVER = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(_RESOLVER)
    resolve_group = _RESOLVER.resolve_group
    merge_cloud_init_sections = _RESOLVER.merge_cloud_init_sections
    canonical_group_name = _RESOLVER.canonical_group_name


def functional_group_setting(
    config_data: Any,
    functional_group: str,
    setting: str,
    legacy_boot_kernel_params: Any = None,
) -> Any:
    """Return one resolved setting for a functional group.

    Args:
        config_data: Parsed ``functional_group_config.yml``, or an empty
            mapping when the optional file is absent.
        functional_group: Exact PXE functional-group name.
        setting: One of ``boot_kernel_params``, ``cloud_init_config_file``,
            ``post_config``, or ``image_override``.

    Returns:
        The resolved value for that setting.
    """
    resolved = resolve_group(
        config_data, functional_group, legacy_boot_kernel_params
    ).values()
    if setting not in resolved:
        raise AnsibleFilterError(
            f"functional_group_setting: unknown setting '{setting}'; "
            f"expected one of {sorted(resolved)}"
        )
    return resolved[setting]


def functional_group_settings(
    config_data: Any,
    functional_group: str,
    legacy_boot_kernel_params: Any = None,
) -> dict[str, Any]:
    """Return every resolved setting for a functional group."""
    return resolve_group(
        config_data, functional_group, legacy_boot_kernel_params
    ).values()


def functional_group_provenance(
    config_data: Any,
    functional_group: str,
    legacy_boot_kernel_params: Any = None,
) -> dict[str, str]:
    """Return the level that supplied each resolved setting."""
    return resolve_group(
        config_data, functional_group, legacy_boot_kernel_params
    ).provenance()


def functional_group_cloud_init(
    base_section: Any, post_config: Any
) -> dict[str, list[Any]]:
    """Merge a resolved cloud-init section with ordered post-configuration."""
    return merge_cloud_init_sections(base_section, post_config)


def functional_group_canonical_name(functional_group: str) -> str:
    """Return the operator-facing name for a runtime functional-group name."""
    return canonical_group_name(functional_group)


class FilterModule:  # pylint: disable=too-few-public-methods
    """Expose the functional-group resolver filters to Ansible."""

    def filters(self) -> dict[str, Any]:
        """Return the filter name to callable mapping."""
        return {
            "functional_group_setting": functional_group_setting,
            "functional_group_settings": functional_group_settings,
            "functional_group_provenance": functional_group_provenance,
            "functional_group_cloud_init": functional_group_cloud_init,
            "functional_group_canonical_name": functional_group_canonical_name,
        }
