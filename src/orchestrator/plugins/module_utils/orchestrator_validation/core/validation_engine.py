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
from ..validators import network_spec_validator, orchestrator_config_validator


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


def logic_storage(
    input_project_dir: str,
    storage_data: Any,
    logger: Logger | None = None,
) -> list[str]:
    """Dispatch storage-reference validation.

    Args:
        input_project_dir: Current project input directory.
        storage_data: Parsed ``storage_config.yml`` data, when present.
        logger: Optional validation logger.

    Returns:
        Storage-reference validation errors.
    """
    return orchestrator_config_validator.validate_storage_references(
        input_project_dir, storage_data, logger
    )
