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
L2 (business logic) validator for build_stream_config.yml.

Validates cross-field constraints that cannot be expressed in JSON Schema:
  - If enable_build_stream is true, build_stream_host_ip and gitlab_host are required
  - Port numbers must be valid
  - Host IP addresses must be non-empty strings
"""


def validate(config_data, logger=None):
    """
    Validate build_stream_config.yml business logic.

    Args:
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
        if logger:
            logger.info(msg.build_stream_disabled_msg())
        return errors

    # When enabled, host IP is mandatory
    host_ip = config_data.get("build_stream_host_ip", "")
    if not host_ip or not str(host_ip).strip():
        errors.append(msg.missing_host_ip_msg())

    # Validate BSM port
    port = config_data.get("build_stream_port", 8010)
    try:
        port_int = int(port)
        if not 1 <= port_int <= 65535:
            errors.append(msg.invalid_port_msg(port))
    except (ValueError, TypeError):
        errors.append(msg.invalid_port_msg(port))

    # GitLab host is mandatory when enabled
    gitlab_host = config_data.get("gitlab_host", "")
    if not gitlab_host or not str(gitlab_host).strip():
        errors.append(msg.missing_gitlab_host_msg())

    # Validate GitLab HTTPS port
    gitlab_port = config_data.get("gitlab_https_port", 443)
    try:
        gitlab_port_int = int(gitlab_port)
        if not 1 <= gitlab_port_int <= 65535:
            errors.append(msg.invalid_gitlab_port_msg(gitlab_port))
    except (ValueError, TypeError):
        errors.append(msg.invalid_gitlab_port_msg(gitlab_port))

    # Warn if BSM and GitLab on same host
    if host_ip and gitlab_host and str(host_ip).strip() == str(gitlab_host).strip():
        warning = msg.same_host_warning_msg()
        if logger:
            logger.warning(warning)

    return errors
