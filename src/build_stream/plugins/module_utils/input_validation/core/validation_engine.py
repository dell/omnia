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
"""Core JSON Schema and business-logic validation entry points."""

from jsonschema import FormatChecker
from jsonschema.exceptions import SchemaError
from jsonschema.validators import validator_for


def _schema_error_path(file_label, validation_error):
    """Return a readable dotted path for a jsonschema validation error."""
    path = ".".join(str(part) for part in validation_error.absolute_path)
    return f"{file_label}.{path}" if path else file_label


def schema(data, schema_def, file_label, errors, logger):
    """
    Validates data against a JSON schema (L1 Validation).

    Uses the validator declared by the schema's ``$schema`` field. Delegating
    to jsonschema ensures that the complete 2.3 schema contract is enforced,
    including types, patterns, string lengths, numeric bounds, nested values,
    and conditionals.

    Args:
        data: Parsed YAML/JSON data to validate.
        schema_def: JSON schema definition dict.
        file_label: Human-readable file label for error messages.
        errors: List to append error messages to.
        logger: Logger instance.
    """
    if not schema_def:
        return

    try:
        validator_class = validator_for(schema_def)
        validator_class.check_schema(schema_def)
    except SchemaError as exc:
        err = f"{file_label}: Invalid JSON schema: {exc.message}"
        errors.append(err)
        logger.error(err)
        return

    validator = validator_class(
        schema_def,
        format_checker=FormatChecker(),
    )
    validation_errors = sorted(
        validator.iter_errors(data),
        key=lambda item: [str(part) for part in item.absolute_path],
    )
    for validation_error in validation_errors:
        path = _schema_error_path(file_label, validation_error)
        err = f"{path}: {validation_error.message}"
        errors.append(err)
        logger.error(err)


def logic(config_data, logger=None):
    """
    Runs L2 (business logic) validation on build_stream_config data.

    Args:
        config_data (dict): Parsed build_stream_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    from ansible.module_utils.input_validation.validators import (  # pylint: disable=E0401,C0415
        build_stream_config_validator,
    )
    return build_stream_config_validator.validate(config_data, logger)


def logic_credentials(cred_data, config_data, logger=None):
    """
    Runs L2 (business logic) validation on credential data.

    Args:
        cred_data (dict): Parsed build_stream_credentials.yml content.
        config_data (dict): Parsed build_stream_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    from ansible.module_utils.input_validation.validators import (  # pylint: disable=E0401,C0415
        build_stream_credentials_validator,
    )
    return build_stream_credentials_validator.validate(
        cred_data, config_data, logger
    )
