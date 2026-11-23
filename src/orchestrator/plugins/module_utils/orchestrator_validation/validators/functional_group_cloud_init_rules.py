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
"""Cloud-init validation rules for functional groups.

Per ER-ORCH-009 FR-2.2, flexible groups support write_files and runcmd
directives only. Secret-bearing content is rejected before publication.
Paths are validated to remain within the active project input boundary.
"""

from __future__ import annotations

import os
import re
import yaml
from logging import Logger
from typing import Any

from ..messages import orchestrator_messages as msg

# Secret patterns that must not appear in cloud-init content
_SECRET_PATTERNS = [
    re.compile(r"password\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"secret\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"token\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
]

# Allowed cloud-init directives for flexible groups
_ALLOWED_DIRECTIVES = {"write_files", "runcmd"}


def _check_secrets(content: str) -> list[str]:
    """Check for secret-bearing patterns in cloud-init content.

    Args:
        content: Cloud-init content to check.

    Returns:
        List of secret pattern matches found.
    """
    secrets = []
    for pattern in _SECRET_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            secrets.extend(matches)
    return secrets


def _validate_cloud_init_directives(
    cloud_init_data: dict[str, Any], referenced_by: str, errors: list[str], logger: Logger | None
) -> None:
    """Validate that only allowed cloud-init directives are present.

    Args:
        cloud_init_data: Parsed cloud-init YAML data.
        referenced_by: Reference path for error messages.
        errors: List to append error messages to.
        logger: Optional validation logger.
    """
    if not isinstance(cloud_init_data, dict):
        return

    unknown = set(cloud_init_data.keys()) - _ALLOWED_DIRECTIVES
    if unknown:
        record_error(
            errors,
            logger,
            msg.functional_group_cloud_init_disallowed_directive_msg(
                referenced_by, sorted(unknown)
            ),
        )


def _validate_write_files(
    write_files: Any, referenced_by: str, errors: list[str], logger: Logger | None
) -> None:
    """Validate write_files directive structure and content.

    Args:
        write_files: write_files value from cloud-init.
        referenced_by: Reference path for error messages.
        errors: List to append error messages to.
        logger: Optional validation logger.
    """
    if not isinstance(write_files, list):
        record_error(
            errors,
            logger,
            msg.functional_group_type_msg(
                f"{referenced_by}.write_files", type(write_files).__name__, "a list"
            ),
        )
        return

    for idx, entry in enumerate(write_files):
        if not isinstance(entry, dict):
            record_error(
                errors,
                logger,
                msg.functional_group_type_msg(
                    f"{referenced_by}.write_files[{idx}]",
                    type(entry).__name__,
                    "a mapping",
                ),
            )
            continue

        # Check required fields
        if "path" not in entry:
            record_error(
                errors,
                logger,
                msg.functional_group_missing_field_msg(
                    f"{referenced_by}.write_files[{idx}]", "path"
                ),
            )
        if "content" not in entry:
            record_error(
                errors,
                logger,
                msg.functional_group_missing_field_msg(
                    f"{referenced_by}.write_files[{idx}]", "content"
                ),
            )

        # Check for secrets in content
        content = entry.get("content", "")
        if isinstance(content, str):
            secrets = _check_secrets(content)
            if secrets:
                record_error(
                    errors,
                    logger,
                    msg.functional_group_cloud_init_secret_msg(
                        f"{referenced_by}.write_files[{idx}]", secrets
                    ),
                )


def _validate_runcmd(
    runcmd: Any, referenced_by: str, errors: list[str], logger: Logger | None
) -> None:
    """Validate runcmd directive structure and content.

    Args:
        runcmd: runcmd value from cloud-init.
        referenced_by: Reference path for error messages.
        errors: List to append error messages to.
        logger: Optional validation logger.
    """
    if not isinstance(runcmd, list):
        record_error(
            errors,
            logger,
            msg.functional_group_type_msg(
                f"{referenced_by}.runcmd", type(runcmd).__name__, "a list"
            ),
        )
        return

    for idx, cmd in enumerate(runcmd):
        if not isinstance(cmd, str):
            record_error(
                errors,
                logger,
                msg.functional_group_type_msg(
                    f"{referenced_by}.runcmd[{idx}]", type(cmd).__name__, "a string"
                ),
            )


def validate_cloud_init_reference(
    scope: dict[str, Any],
    referenced_by: str,
    input_project_dir: str,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate a cloud-init configuration reference.

    Args:
        scope: Configuration scope (common or group).
        referenced_by: Reference path for error messages.
        input_project_dir: Current project input directory.
        errors: List to append error messages to.
        logger: Optional validation logger.
    """
    cloud_init = scope.get("cloud_init")
    if not isinstance(cloud_init, dict):
        return

    config_file = cloud_init.get("config_file")
    if not isinstance(config_file, str) or not config_file.strip():
        return

    # Validate path stays within project input boundary
    config_file = config_file.strip()
    if not os.path.isabs(config_file):
        # Relative path: resolve against project input directory
        full_path = os.path.normpath(os.path.join(input_project_dir, config_file))
    else:
        # Absolute path: check it doesn't escape project input
        full_path = os.path.normpath(config_file)

    project_dir_norm = os.path.normpath(input_project_dir)
    if not full_path.startswith(project_dir_norm):
        record_error(
            errors,
            logger,
            msg.functional_group_path_escaped_msg(referenced_by, config_file),
        )
        return

    # Check file exists
    if not os.path.isfile(full_path):
        record_error(
            errors,
            logger,
            msg.functional_group_path_not_found_msg(referenced_by, config_file),
        )
        return

    # Read and validate cloud-init content
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            cloud_init_data = yaml.safe_load(f)

        if not isinstance(cloud_init_data, dict):
            record_error(
                errors,
                logger,
                msg.functional_group_type_msg(
                    f"{referenced_by}.cloud_init content",
                    type(cloud_init_data).__name__,
                    "a mapping",
                ),
            )
            return

        _validate_cloud_init_directives(cloud_init_data, referenced_by, errors, logger)

        if "write_files" in cloud_init_data:
            _validate_write_files(
                cloud_init_data["write_files"], referenced_by, errors, logger
            )

        if "runcmd" in cloud_init_data:
            _validate_runcmd(cloud_init_data["runcmd"], referenced_by, errors, logger)

    except yaml.YAMLError as e:
        record_error(
            errors,
            logger,
            msg.functional_group_cloud_init_parse_msg(referenced_by, str(e)),
        )
    except (OSError, IOError) as e:
        record_error(
            errors,
            logger,
            msg.functional_group_cloud_init_read_msg(referenced_by, str(e)),
        )


def record_error(errors: list[str], logger: Logger | None, message: str) -> None:
    """Append an error and write it to the validation log when configured."""
    errors.append(message)
    if logger:
        logger.error(message)
