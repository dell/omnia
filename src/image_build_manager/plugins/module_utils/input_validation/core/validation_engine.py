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
"""
Validation Engine - Core validation orchestration.

This module provides the main entry points for:
- L1 Validation: JSON Schema validation
- L2 Validation: Business logic validation (routed to validators/)

It orchestrates the validation process and routes to appropriate validators.
"""
from ansible.module_utils.input_validation.messages import image_build_messages as msg  # pylint: disable=E0401


def schema(data, schema_def, file_label, errors, logger):
    """
    Validates data against a JSON schema (L1 Validation).

    Uses basic type/required/enum checks without jsonschema dependency.

    Args:
        data: Parsed YAML/JSON data to validate.
        schema_def: JSON schema definition dict.
        file_label: Human-readable file label for error messages.
        errors: List to append error messages to.
        logger: Logger instance.
    """
    if not schema_def or not data:
        return

    schema_type = schema_def.get("type")
    if schema_type == "object" and not isinstance(data, dict):
        err = msg.schema_type_mismatch_msg(file_label, "object", type(data).__name__)
        errors.append(err)
        logger.error(err)
        return

    # Check required properties
    required = schema_def.get("required", [])
    properties = schema_def.get("properties", {})
    for req_key in required:
        if req_key not in data:
            err = msg.missing_required_property_msg(file_label, req_key)
            errors.append(err)
            logger.error(err)

    # Check enum constraints
    for prop_name, prop_schema in properties.items():
        if prop_name not in data:
            continue
        value = data[prop_name]

        if "enum" in prop_schema and value not in prop_schema["enum"]:
            err = msg.invalid_enum_value_msg(
                file_label, prop_name, value, prop_schema["enum"]
            )
            errors.append(err)
            logger.error(err)

        # Recurse into nested objects
        if prop_schema.get("type") == "object" and isinstance(value, dict):
            schema(
                value, prop_schema, f"{file_label}.{prop_name}", errors, logger
            )

    # Check additionalProperties constraint
    if schema_def.get("additionalProperties") is False:
        extra_keys = set(data.keys()) - set(properties.keys())
        for extra in extra_keys:
            err = msg.unexpected_property_msg(file_label, extra)
            errors.append(err)
            logger.error(err)


def logic(config_data, logger=None):
    """
    Runs L2 (business logic) validation on image_build_config data.

    Args:
        config_data (dict): Parsed image_build_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    from ansible.module_utils.input_validation.validators import (  # pylint: disable=E0401,C0415
        image_build_config_validator,
    )
    return image_build_config_validator.validate(config_data, logger)


def logic_catalog(catalog_file, logger=None):
    """
    Runs L2 (referential integrity) validation on catalog JSON.

    Args:
        catalog_file (str): Absolute path to catalog JSON file.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    from ansible.module_utils.input_validation.validators import (  # pylint: disable=E0401,C0415
        catalog_validator,
    )
    return catalog_validator.validate(catalog_file, logger)


def logic_credentials(cred_data, config_data, logger=None):
    """
    Runs L2 (business logic) validation on credential data.

    Args:
        cred_data (dict): Parsed image_build_credentials.yml content.
        config_data (dict): Parsed image_build_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    from ansible.module_utils.input_validation.validators import (  # pylint: disable=E0401,C0415
        image_build_credentials_validator,
    )
    return image_build_credentials_validator.validate(
        cred_data, config_data, logger
    )
