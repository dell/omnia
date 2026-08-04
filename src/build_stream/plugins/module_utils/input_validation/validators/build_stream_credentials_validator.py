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
L2 (business logic) validator for build_stream_credentials.yml.

Validates cross-field credential constraints:
  - When enable_build_stream is true, mandatory credentials must be present
  - postgres_user/password required for database deployment
"""


def validate(cred_data, config_data, logger=None):
    """
    Validate build_stream_credentials.yml business logic.

    Args:
        cred_data (dict): Parsed build_stream_credentials.yml content.
        config_data (dict): Parsed build_stream_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    from ansible.module_utils.input_validation.messages import (  # pylint: disable=E0401,C0415
        build_stream_messages as msg,
    )

    errors = []
    enable = config_data.get("enable_build_stream", False)

    if not enable:
        return errors

    # Mandatory credentials when build_stream is enabled
    mandatory_fields = ["gitlab_root_password", "gitlab_ssh_password"]
    for field in mandatory_fields:
        value = cred_data.get(field, "")
        if not value or not str(value).strip():
            errors.append(msg.missing_credential_msg(field))

    # Postgres credentials are required for database deployment
    postgres_fields = ["postgres_user", "postgres_password"]
    for field in postgres_fields:
        value = cred_data.get(field, "")
        if not value or not str(value).strip():
            errors.append(msg.missing_credential_msg(field))

    return errors
