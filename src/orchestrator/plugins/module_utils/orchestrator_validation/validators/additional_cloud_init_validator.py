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
"""L2 validation for user-provided additional cloud-init configuration."""

from __future__ import annotations

import csv
import os
import re
from logging import Logger
from typing import Any

import yaml

from ..messages import orchestrator_messages as msg
from .pxe_mapping_validator import read_mapping, resolve_mapping_path


ALLOWED_TOP_LEVEL_KEYS = frozenset({"common", "groups"})
ALLOWED_SECTION_KEYS = frozenset({"write_files", "runcmd"})
PROHIBITED_SECTION_KEYS = frozenset(
    {"bootcmd", "network", "network-config", "packages"}
)
ALLOWED_WRITE_FILE_KEYS = frozenset(
    {"path", "content", "permissions", "owner", "append", "encoding"}
)
ALLOWED_ENCODINGS = frozenset(
    {
        "b64",
        "base64",
        "gz",
        "gzip",
        "gz+b64",
        "gz+base64",
        "gzip+b64",
        "gzip+base64",
    }
)
PERMISSIONS_PATTERN = re.compile(r"^0[0-7]{3}$")
REQUIRED_WRITE_FILE_KEYS = ("path",)
STRING_WRITE_FILE_KEYS = (
    "path",
    "content",
    "permissions",
    "owner",
    "encoding",
)


def _record_error(
    errors: list[str], logger: Logger | None, message: str
) -> None:
    """Append an error and write it to the validation log when configured."""
    errors.append(message)
    if logger:
        logger.error(message)


def _read_functional_group_names(mapping_path: str) -> set[str] | None:
    """Read selected functional-group names from a valid PXE mapping file.

    A missing/unreadable file or missing functional-group header is already
    reported by the PXE mapping validator, so those conditions return ``None``
    here to avoid emitting a misleading cloud-init group error.
    """
    if not os.path.isfile(mapping_path):
        return None

    try:
        _, header, numbered_rows = read_mapping(mapping_path)
        if "FUNCTIONAL_GROUP_NAME" not in header:
            return None
        group_index = header.index("FUNCTIONAL_GROUP_NAME")
        return {
            row[group_index].strip()
            for _, row in numbered_rows
            if group_index < len(row) and row[group_index].strip()
        }
    except (csv.Error, OSError, UnicodeError):
        return None


def _validate_write_file_entry(
    entry: Any,
    entry_path: str,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate one entry supported by the metadata-service template."""
    if not isinstance(entry, dict):
        _record_error(
            errors,
            logger,
            msg.cloud_init_type_msg(
                entry_path, type(entry).__name__, "a mapping"
            ),
        )
        return

    for key in entry:
        if key not in ALLOWED_WRITE_FILE_KEYS:
            _record_error(
                errors,
                logger,
                msg.cloud_init_unknown_key_msg(
                    f"{entry_path}.{key}",
                    str(key),
                    "path, content, permissions, owner, append, and encoding",
                ),
            )

    for key in REQUIRED_WRITE_FILE_KEYS:
        value = entry.get(key)
        if not isinstance(value, str) or not value.strip():
            _record_error(
                errors,
                logger,
                msg.cloud_init_required_field_msg(entry_path, key),
            )

    for key in STRING_WRITE_FILE_KEYS:
        if key not in entry or key in REQUIRED_WRITE_FILE_KEYS:
            continue
        if not isinstance(entry[key], str):
            _record_error(
                errors,
                logger,
                msg.cloud_init_type_msg(
                    f"{entry_path}.{key}",
                    type(entry[key]).__name__,
                    "a string",
                ),
            )

    permissions = entry.get("permissions")
    if isinstance(permissions, str) and not PERMISSIONS_PATTERN.fullmatch(
        permissions
    ):
        _record_error(
            errors,
            logger,
            msg.cloud_init_invalid_value_msg(
                f"{entry_path}.permissions",
                permissions,
                "a four-digit octal mode such as 0644",
            ),
        )

    encoding = entry.get("encoding")
    if isinstance(encoding, str) and encoding not in ALLOWED_ENCODINGS:
        _record_error(
            errors,
            logger,
            msg.cloud_init_invalid_value_msg(
                f"{entry_path}.encoding",
                encoding,
                ", ".join(sorted(ALLOWED_ENCODINGS)),
            ),
        )

    if "append" in entry and not isinstance(entry["append"], bool):
        _record_error(
            errors,
            logger,
            msg.cloud_init_type_msg(
                f"{entry_path}.append",
                type(entry["append"]).__name__,
                "a boolean",
            ),
        )


def _validate_section(
    section_data: Any,
    section_path: str,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate a common or functional-group cloud-init section."""
    if not isinstance(section_data, dict):
        _record_error(
            errors,
            logger,
            msg.cloud_init_type_msg(
                section_path, type(section_data).__name__, "a mapping"
            ),
        )
        return

    for key in section_data:
        key_path = f"{section_path}.{key}"
        if key in PROHIBITED_SECTION_KEYS:
            _record_error(
                errors,
                logger,
                msg.cloud_init_prohibited_key_msg(key_path, str(key)),
            )
        elif key not in ALLOWED_SECTION_KEYS:
            _record_error(
                errors,
                logger,
                msg.cloud_init_unknown_key_msg(
                    key_path, str(key), "write_files and runcmd"
                ),
            )

    if "write_files" in section_data:
        write_files = section_data["write_files"]
        if not isinstance(write_files, list):
            _record_error(
                errors,
                logger,
                msg.cloud_init_type_msg(
                    f"{section_path}.write_files",
                    type(write_files).__name__,
                    "a list",
                ),
            )
        else:
            for index, entry in enumerate(write_files):
                _validate_write_file_entry(
                    entry,
                    f"{section_path}.write_files[{index}]",
                    errors,
                    logger,
                )

    if "runcmd" in section_data:
        run_commands = section_data["runcmd"]
        if not isinstance(run_commands, list):
            _record_error(
                errors,
                logger,
                msg.cloud_init_type_msg(
                    f"{section_path}.runcmd",
                    type(run_commands).__name__,
                    "a list",
                ),
            )
        else:
            for index, command in enumerate(run_commands):
                if not isinstance(command, str):
                    command_path = f"{section_path}.runcmd[{index}]"
                    _record_error(
                        errors,
                        logger,
                        msg.cloud_init_type_msg(
                            command_path,
                            type(command).__name__,
                            "a string",
                        ),
                    )


def _validate_document(
    cloud_init_data: Any,
    functional_group_names: set[str] | None,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate the parsed additional cloud-init document."""
    if cloud_init_data is None:
        return

    if not isinstance(cloud_init_data, dict):
        _record_error(
            errors,
            logger,
            msg.cloud_init_type_msg(
                "additional_cloud_init",
                type(cloud_init_data).__name__,
                "a mapping",
            ),
        )
        return

    for key in cloud_init_data:
        if key not in ALLOWED_TOP_LEVEL_KEYS:
            _record_error(
                errors,
                logger,
                msg.cloud_init_unknown_key_msg(
                    f"additional_cloud_init.{key}",
                    str(key),
                    "common and groups",
                ),
            )

    if "common" in cloud_init_data:
        _validate_section(
            cloud_init_data["common"],
            "additional_cloud_init.common",
            errors,
            logger,
        )

    if "groups" not in cloud_init_data:
        return
    groups = cloud_init_data["groups"]
    if not isinstance(groups, dict):
        _record_error(
            errors,
            logger,
            msg.cloud_init_type_msg(
                "additional_cloud_init.groups",
                type(groups).__name__,
                "a mapping",
            ),
        )
        return

    for group_name, section_data in groups.items():
        if not isinstance(group_name, str) or not group_name.strip():
            _record_error(
                errors,
                logger,
                msg.cloud_init_type_msg(
                    "additional_cloud_init.groups key",
                    type(group_name).__name__,
                    "a non-empty string",
                ),
            )
            continue
        if (
            functional_group_names is not None
            and group_name not in functional_group_names
        ):
            _record_error(
                errors,
                logger,
                msg.cloud_init_invalid_group_msg(group_name),
            )
        _validate_section(
            section_data,
            f"additional_cloud_init.groups.{group_name}",
            errors,
            logger,
        )


def validate(
    config_data: dict[str, Any],
    input_project_dir: str,
    logger: Logger | None = None,
) -> list[str]:
    """Validate the configured additional cloud-init file.

    Args:
        config_data: Parsed ``orchestrator_config.yml`` data.
        input_project_dir: Project input directory used for the default PXE
            mapping path.
        logger: Optional validation logger.

    Returns:
        Validation error messages, or an empty list for valid/disabled input.
    """
    errors: list[str] = []
    configured_path = config_data.get("additional_cloud_init_config_file", "")
    if not isinstance(configured_path, str) or not configured_path.strip():
        return errors

    cloud_init_path = os.path.realpath(configured_path.strip())
    if not os.path.isfile(cloud_init_path):
        _record_error(
            errors,
            logger,
            msg.cloud_init_file_missing_msg(configured_path.strip()),
        )
        return errors

    try:
        with open(cloud_init_path, "r", encoding="utf-8") as cloud_init_file:
            cloud_init_data = yaml.safe_load(cloud_init_file)
    except yaml.YAMLError as exc:
        _record_error(
            errors,
            logger,
            msg.cloud_init_yaml_parse_failed_msg(
                cloud_init_path, type(exc).__name__
            ),
        )
        return errors
    except (OSError, UnicodeError) as exc:
        _record_error(
            errors,
            logger,
            msg.cloud_init_read_failed_msg(
                cloud_init_path, type(exc).__name__
            ),
        )
        return errors

    mapping_path = resolve_mapping_path(config_data, input_project_dir)
    functional_groups = _read_functional_group_names(mapping_path)
    _validate_document(cloud_init_data, functional_groups, errors, logger)
    return errors
