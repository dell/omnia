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
"""L2 validation for ``functional_group_config.yml``.

Every rule here fails *before* any node is mutated. Schema validation covers
structure; this module orchestrates the semantic rules JSON Schema cannot
express: per-field legacy conflicts, group keys against the PXE mapping, and
the scope rules in ``functional_group_rules`` and
``functional_group_cloud_init_rules``.
"""

from __future__ import annotations

import os
from logging import Logger
from typing import Any, Callable

from ..messages import orchestrator_messages as msg
from ...functional_group_resolver import resolve_group
from .additional_cloud_init_validator import _read_functional_group_names
from .functional_group_cloud_init_rules import (
    validate_cloud_init_reference,
    validate_post_config,
)
from .functional_group_rules import (
    SUPPORTED_ARCHITECTURES,
    group_architecture,
    record_error,
    validate_architecture_reference,
    validate_image_override,
    validate_kernel_params,
    warn_unsupported_os,
)
from .pxe_mapping_validator import resolve_mapping_path


def is_applicable(input_project_dir: str) -> bool:
    """Return whether this optional input is present for the project."""
    return os.path.isfile(os.path.join(input_project_dir, "functional_group_config.yml"))


def _non_empty(value: Any) -> bool:
    """Return whether a value overrides rather than inherits."""
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def _any_scope(config_data: dict[str, Any], predicate: Callable[[dict], bool]) -> bool:
    """Return whether ``common`` or any group scope satisfies *predicate*."""
    scopes = [config_data.get("common")]
    groups = config_data.get("groups")
    if isinstance(groups, dict):
        scopes.extend(groups.values())
    return any(isinstance(scope, dict) and predicate(scope) for scope in scopes)


def _sets_cloud_init(scope: dict[str, Any]) -> bool:
    cloud_init = scope.get("cloud_init")
    config_file = cloud_init.get("config_file") if isinstance(cloud_init, dict) else None
    return _non_empty(config_file) or _non_empty(scope.get("post_config"))


def _sets_kernel_params(scope: dict[str, Any]) -> bool:
    return _non_empty(scope.get("boot_kernel_params"))


def _validate_legacy_inputs(
    config_data: dict[str, Any],
    orchestrator_data: Any,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Reject non-empty legacy values combined with their new counterparts.

    A legacy value may only fill in where the corresponding new value is empty
    (FR-1.2), so each legacy input conflicts only with its own field family.
    """
    legacy = orchestrator_data if isinstance(orchestrator_data, dict) else {}
    legacy_cloud_init = legacy.get("additional_cloud_init_config_file", "")
    if _non_empty(legacy_cloud_init) and _any_scope(config_data, _sets_cloud_init):
        record_error(errors, logger, msg.functional_group_legacy_conflict_msg())

    legacy_kernel = legacy.get("boot_kernel_params", "")
    if _non_empty(legacy_kernel):
        validate_kernel_params(
            legacy_kernel, "orchestrator_config", errors, logger
        )
        if _any_scope(config_data, _sets_kernel_params):
            record_error(errors, logger, msg.functional_group_legacy_kernel_conflict_msg())


def _validate_scope(
    scope: Any,
    referenced_by: str,
    input_project_dir: str,
    errors: list[str],
    logger: Logger | None,
) -> dict[str, Any]:
    """Validate one ``common`` or group scope and return it as a mapping."""
    if scope is None:
        return {}
    if not isinstance(scope, dict):
        record_error(
            errors,
            logger,
            msg.functional_group_type_msg(referenced_by, type(scope).__name__, "a mapping"),
        )
        return {}
    validate_kernel_params(scope.get("boot_kernel_params"), referenced_by, errors, logger)
    validate_cloud_init_reference(scope, referenced_by, input_project_dir, errors, logger)
    validate_post_config(scope, referenced_by, errors, logger)
    return scope


def _validate_groups(
    config_data: dict[str, Any],
    groups: dict[str, Any],
    known_groups: set[str] | None,
    input_project_dir: str,
    errors: list[str],
    logger: Logger | None,
    warnings: list[str] | None,
) -> None:
    """Validate explicit group scopes and inherited cloud-init architecture."""
    for group, scope in groups.items():
        # `known_groups is None` means the mapping itself is unreadable, which
        # the PXE validator reports; avoid a misleading second error here.
        if known_groups is not None and group not in known_groups:
            record_error(errors, logger, msg.functional_group_unknown_group_msg(group))
        if group_architecture(group) is None:
            record_error(
                errors,
                logger,
                msg.functional_group_architecture_required_msg(group, SUPPORTED_ARCHITECTURES),
            )
        validated = _validate_scope(
            scope, f"groups.{group}", input_project_dir, errors, logger
        )
        validate_image_override(group, validated, errors, logger)
        warn_unsupported_os(group, logger, warnings)

    # A common cloud-init file applies even when no explicit group scope exists.
    # Resolve every mapped group so architecture validation cannot be bypassed.
    for group in sorted(known_groups if known_groups is not None else groups):
        resolved = resolve_group(config_data, group).cloud_init_config_file.value
        if isinstance(resolved, str) and resolved.strip():
            validate_architecture_reference(
                group, resolved, "cloud_init.config_file", errors, logger
            )


def validate(
    config_data: Any,
    orchestrator_data: Any,
    input_project_dir: str,
    logger: Logger | None = None,
    warnings: list[str] | None = None,
) -> list[str]:
    """Validate ``functional_group_config.yml``.

    Args:
        config_data: Parsed ``functional_group_config.yml`` data, or ``None``
            when the file is absent or contains no document.
        orchestrator_data: Parsed ``orchestrator_config.yml`` data, used for
            the legacy compatibility rules.
        input_project_dir: Current project input directory.
        logger: Optional validation logger.
        warnings: Optional result list for non-blocking operator warnings.

    Returns:
        Validation error messages, or an empty list for valid/absent input.
    """
    errors: list[str] = []
    if config_data is None:
        return errors
    if not isinstance(config_data, dict):
        record_error(
            errors,
            logger,
            msg.functional_group_type_msg(
                "functional_group_config", type(config_data).__name__, "a mapping"
            ),
        )
        return errors

    _validate_legacy_inputs(config_data, orchestrator_data, errors, logger)
    _validate_scope(config_data.get("common"), "common", input_project_dir, errors, logger)

    groups = config_data.get("groups") or {}
    if not isinstance(groups, dict):
        record_error(
            errors,
            logger,
            msg.functional_group_type_msg("groups", type(groups).__name__, "a mapping"),
        )
        return errors

    mapping_path = resolve_mapping_path(
        orchestrator_data if isinstance(orchestrator_data, dict) else {},
        input_project_dir,
    )
    _validate_groups(
        config_data,
        groups,
        _read_functional_group_names(mapping_path),
        input_project_dir,
        errors,
        logger,
        warnings,
    )
    return errors
