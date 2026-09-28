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
"""L2 semantic and cross-file validation for Orchestrator configuration."""

from __future__ import annotations

from logging import Logger
from typing import Any

from ..messages import orchestrator_messages as msg
from .network_spec_validator import record_error


def _validate_language(
    config_data: dict[str, Any], errors: list[str], logger: Logger | None
) -> None:
    """Validate the supported provisioning language."""
    language = config_data.get("language", "")
    if not language:
        record_error(errors, logger, msg.LANGUAGE_REQUIRED_MSG)
    elif "en_US.UTF-8" not in language:
        record_error(errors, logger, msg.language_unsupported_msg(language))


def _validate_default_lease_time(
    config_data: dict[str, Any], errors: list[str], logger: Logger | None
) -> None:
    """Validate that the DHCP lease time is a positive integer."""
    lease_time = config_data.get("default_lease_time", "")
    try:
        if int(lease_time) <= 0:
            raise ValueError("non-positive lease time")
    except (TypeError, ValueError):
        record_error(errors, logger, msg.lease_time_invalid_msg(lease_time))


def _validate_s3_config(
    config_data: dict[str, Any], errors: list[str], logger: Logger | None
) -> None:
    """Preserve validation of legacy S3 provider and endpoint fields."""
    provider = config_data.get("s3_storage_provider", "minio")
    endpoint = config_data.get("s3_endpoint", "")
    if provider in ("powerscale", "external") and (
        not isinstance(endpoint, str) or not endpoint.strip()
    ):
        record_error(errors, logger, msg.s3_endpoint_required_msg(provider))
    if provider == "minio" and endpoint and logger:
        logger.warning(msg.s3_endpoint_ignored_msg())


def validate(
    config_data: dict[str, Any],
    input_project_dir: str,
    logger: Logger | None = None,
) -> list[str]:
    """Run all L2 Orchestrator configuration checks.

    Args:
        config_data: Parsed ``orchestrator_config.yml`` data.
        input_project_dir: Current project input directory used for defaults.
        logger: Optional validation logger.

    Returns:
        Validation error messages, or an empty list for valid input.
    """
    del input_project_dir  # Reserved for the common validator interface.
    errors: list[str] = []
    _validate_language(config_data, errors, logger)
    _validate_default_lease_time(config_data, errors, logger)
    _validate_s3_config(config_data, errors, logger)
    return errors
