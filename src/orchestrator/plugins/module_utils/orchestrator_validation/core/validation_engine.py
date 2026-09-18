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
"""Central JSON Schema and L2 validation dispatch for Orchestrator."""

from __future__ import annotations

from logging import Logger
from typing import Any

from jsonschema import FormatChecker
from jsonschema.exceptions import SchemaError
from jsonschema.validators import validator_for

from ..messages import orchestrator_messages as msg
from ..validators import (
    additional_cloud_init_validator,
    high_availability_validator,
    network_spec_validator,
    omnia_config_validator,
    orchestrator_config_validator,
    pxe_mapping_validator,
    security_config_validator,
    storage_config_validator,
)


def _schema_error_path(file_label: str, validation_error: Any) -> str:
    """Return a readable dotted path for a JSON Schema validation error."""
    path = ".".join(str(part) for part in validation_error.absolute_path)
    return f"{file_label}.{path}" if path else file_label


def schema(
    data: Any,
    schema_definition: dict[str, Any],
    file_label: str,
    logger: Logger,
) -> list[str]:
    """Validate parsed input against its declared JSON Schema.

    Args:
        data: Parsed YAML or JSON content.
        schema_definition: JSON Schema document.
        file_label: User-facing source filename.
        logger: Validation logger.

    Returns:
        JSON Schema errors, or an empty list for valid input.
    """
    errors: list[str] = []
    try:
        validator_class = validator_for(schema_definition)
        validator_class.check_schema(schema_definition)
    except SchemaError as exc:
        error = msg.invalid_schema_msg(file_label, exc.message)
        errors.append(error)
        logger.error(error)
        return errors

    validator = validator_class(
        schema_definition,
        format_checker=FormatChecker(),
    )
    validation_errors = sorted(
        validator.iter_errors(data),
        key=lambda item: [str(part) for part in item.absolute_path],
    )
    for validation_error in validation_errors:
        path = _schema_error_path(file_label, validation_error)
        error = msg.schema_validation_msg(path, validation_error.message)
        errors.append(error)
        logger.error(error)
    return errors


def logic(
    config_data: dict[str, Any],
    input_project_dir: str,
    logger: Logger | None = None,
) -> list[str]:
    """Dispatch Orchestrator configuration L2 validation.

    Args:
        config_data: Parsed ``orchestrator_config.yml`` data.
        input_project_dir: Current project input directory.
        logger: Optional validation logger.

    Returns:
        L2 validation errors.
    """
    return orchestrator_config_validator.validate(
        config_data, input_project_dir, logger
    )


def logic_network(
    network_data: dict[str, Any], logger: Logger | None = None
) -> list[str]:
    """Dispatch network specification L2 validation.

    Args:
        network_data: Parsed ``network_spec.yml`` data.
        logger: Optional validation logger.

    Returns:
        L2 validation errors.
    """
    return network_spec_validator.validate(network_data, logger)


def logic_omnia(
    config_data: Any,
    input_project_dir: str,
    logger: Logger | None = None,
    file_statuses: dict[str, bool] | None = None,
    auxiliary_errors: list[str] | None = None,
) -> list[str]:
    """Dispatch ``omnia_config.yml`` L2 validation.

    Args:
        config_data: Parsed ``omnia_config.yml`` data.
        input_project_dir: Current project input directory.
        logger: Optional validation logger.

    Returns:
        L2 validation errors.
    """
    return omnia_config_validator.validate(
        config_data,
        input_project_dir,
        logger,
        file_statuses,
        auxiliary_errors,
    )


def logic_pxe_mapping(
    config_data: dict[str, Any],
    input_project_dir: str,
    logger: Logger | None = None,
) -> list[str]:
    """Dispatch PXE mapping L2 validation."""
    return pxe_mapping_validator.validate(
        config_data, input_project_dir, logger
    )


def logic_additional_cloud_init(
    config_data: dict[str, Any],
    input_project_dir: str,
    logger: Logger | None = None,
) -> list[str]:
    """Dispatch additional cloud-init L2 validation."""
    return additional_cloud_init_validator.validate(
        config_data, input_project_dir, logger
    )


def logic_high_availability(
    config_data: Any,
    input_project_dir: str,
    logger: Logger | None = None,
) -> list[str]:
    """Dispatch Kubernetes high-availability L2 validation."""
    return high_availability_validator.validate(
        config_data, input_project_dir, logger
    )


def logic_security(
    config_data: Any,
    logger: Logger | None = None,
) -> list[str]:
    """Dispatch ``security_config.yml`` L2 validation."""
    return security_config_validator.validate(config_data, logger)


def logic_storage(
    config_data: Any,
    orchestrator_data: dict[str, Any],
    omnia_data: dict[str, Any],
    input_project_dir: str,
    logger: Logger | None = None,
) -> list[str]:
    """Dispatch ``storage_config.yml`` L2 validation."""
    return storage_config_validator.validate(
        config_data,
        orchestrator_data,
        omnia_data,
        input_project_dir,
        logger,
    )


def high_availability_applicable(input_project_dir: str) -> bool:
    """Return whether high-availability input applies to this project."""
    return high_availability_validator.is_applicable(input_project_dir)
