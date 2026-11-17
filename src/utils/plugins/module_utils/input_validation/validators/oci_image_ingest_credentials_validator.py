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
# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-CONFIG-001.5, CG-CRYPTO-001.6
# ****
"""
OCI image ingest credentials validator.

Validates the decrypted oci_image_ingest_credentials content for required,
well-formed registry_username and registry_password. Messages name the field
only; credential values are never echoed.
"""
import re

from ansible.module_utils.input_validation.messages import (  # pylint: disable=E0401
    utils_messages as msg,
)

REQUIRED_FIELDS = ("registry_username", "registry_password")
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def format_schema_error(err):
    """Format a jsonschema error without ever including the offending value."""
    field = str(err.absolute_path[-1]) if err.absolute_path else ""
    if err.validator == "required":
        return err.message
    if err.validator == "additionalProperties":
        return err.message
    return msg.OCI_CRED_INVALID_MSG.format(field=field or "<root>")


def validate(cred_data, logger=None):
    """
    Run L2 validation rules on the credentials content.

    Args:
        cred_data (dict): Decrypted credentials content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid). Never contains values.
    """
    errors = []
    if not isinstance(cred_data, dict):
        errors.append(msg.OCI_CRED_NOT_MAPPING_MSG)
    else:
        for field in REQUIRED_FIELDS:
            value = cred_data.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(msg.OCI_CRED_REQUIRED_MSG.format(field=field))
            elif CONTROL_CHARS.search(value):
                errors.append(msg.OCI_CRED_INVALID_MSG.format(field=field))
        user = cred_data.get("registry_username")
        if isinstance(user, str) and user.strip() and re.search(r"\s", user) \
                and not CONTROL_CHARS.search(user):
            errors.append(msg.OCI_CRED_INVALID_MSG.format(field="registry_username"))
    if logger:
        for error in errors:
            logger.error(error)
    return errors
