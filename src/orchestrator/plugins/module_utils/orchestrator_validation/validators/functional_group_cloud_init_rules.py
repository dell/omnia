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
"""Referenced cloud-init file and ``post_config`` rules for functional groups."""

from __future__ import annotations

import os
import re
from logging import Logger
from typing import Any

import yaml

from ..messages import orchestrator_messages as msg
from .additional_cloud_init_validator import _validate_section
from .functional_group_rules import record_error

#: Keys whose plaintext presence indicates a leaked secret.
_SECRET_KEY_PATTERN = re.compile(
    r"\b(password|passwd|secret|token|private_key|api_key)\b\s*[:=]\s*\S",
    re.IGNORECASE,
)
_VAULT_HEADER = "$ANSIBLE_VAULT"


def _is_within(path: str, root: str) -> bool:
    """Return whether *path* resolves within *root*."""
    try:
        return os.path.commonpath((path, root)) == root
    except ValueError:
        return False


def allowed_roots(input_project_dir: str) -> list[str]:
    """Return the real roots from which privileged cloud-init may be loaded.

    Only the active project's input directory is approved, so one project
    cannot reference another project's or another domain's data.
    """
    return [os.path.realpath(input_project_dir)]


def _read_reference(
    configured: str,
    referenced_by: str,
    input_project_dir: str,
    errors: list[str],
    logger: Logger | None,
) -> str | None:
    """Return a referenced file's content, or ``None`` after recording why not."""
    path = os.path.realpath(configured)
    roots = allowed_roots(input_project_dir)
    if not any(_is_within(path, root) for root in roots):
        record_error(
            errors,
            logger,
            msg.functional_group_file_outside_allowed_root_msg(configured, roots),
        )
        return None
    if not os.path.isfile(path):
        record_error(
            errors, logger, msg.functional_group_file_missing_msg(configured, referenced_by)
        )
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeError) as exc:
        record_error(
            errors, logger, msg.functional_group_file_unreadable_msg(path, type(exc).__name__)
        )
        return None


def validate_cloud_init_reference(
    scope: dict[str, Any],
    referenced_by: str,
    input_project_dir: str,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate a scope's referenced ``cloud_init.config_file``."""
    cloud_init = scope.get("cloud_init")
    if cloud_init is None:
        return
    if not isinstance(cloud_init, dict):
        record_error(
            errors,
            logger,
            msg.functional_group_type_msg(
                f"{referenced_by}.cloud_init", type(cloud_init).__name__, "a mapping"
            ),
        )
        return
    configured = cloud_init.get("config_file")
    if not isinstance(configured, str) or not configured.strip():
        return

    file_ref = f"{referenced_by}.cloud_init.config_file"
    content = _read_reference(
        configured.strip(), file_ref, input_project_dir, errors, logger
    )
    if content is None:
        return
    if content.lstrip().startswith(_VAULT_HEADER):
        # The file is published as cloud-init metadata, so it must not carry
        # secrets; an encrypted file also cannot be structure-validated here.
        record_error(errors, logger, msg.functional_group_file_vault_msg(configured.strip()))
        return
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        record_error(
            errors,
            logger,
            msg.functional_group_yaml_parse_failed_msg(configured.strip(), type(exc).__name__),
        )
        return
    if not data:
        record_error(errors, logger, msg.functional_group_file_empty_msg(configured.strip()))
        return
    _validate_section(data, file_ref, errors, logger)
    if _SECRET_KEY_PATTERN.search(content):
        record_error(errors, logger, msg.functional_group_plaintext_secret_msg(file_ref))


def validate_post_config(
    scope: dict[str, Any],
    referenced_by: str,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate ``post_config`` entries with the additional cloud-init rules."""
    entries = scope.get("post_config")
    if entries is None:
        return
    if not isinstance(entries, list):
        record_error(
            errors,
            logger,
            msg.functional_group_type_msg(
                f"{referenced_by}.post_config", type(entries).__name__, "a list"
            ),
        )
        return
    for index, entry in enumerate(entries):
        entry_path = f"{referenced_by}.post_config[{index}]"
        _validate_section(entry, entry_path, errors, logger)
        if _SECRET_KEY_PATTERN.search(yaml.safe_dump(entry, default_flow_style=False)):
            record_error(errors, logger, msg.functional_group_plaintext_secret_msg(entry_path))
