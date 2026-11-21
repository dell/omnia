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
  - If enable_build_stream is true, build_stream_host_ip and gitlab_mode are required
  - gitlab_mode self_hosted requires gitlab_host; external requires
    gitlab_external_url and gitlab_project_namespace (ER-BSM-003)
  - gitlab_ca_cert_path, when set, must be an existing PEM CA bundle
  - Port numbers must be valid
  - Host IP addresses must be non-empty strings
  - log_tail_lines_default and log_ci_preview_lines must not exceed log_tail_lines_max
"""

from typing import List

GITLAB_MODES = ("self_hosted", "external")


def validate(config_data, logger=None) -> List[str]:
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

    gitlab_mode = config_data.get("gitlab_mode")
    gitlab_host = config_data.get("gitlab_host", "")
    if gitlab_mode not in GITLAB_MODES:
        errors.append(msg.invalid_gitlab_mode_msg())
    elif gitlab_mode == "self_hosted":
        if not gitlab_host or not str(gitlab_host).strip():
            errors.append(msg.missing_gitlab_host_msg())
        if _is_set(config_data, "gitlab_external_url") or _is_set(
            config_data, "gitlab_project_namespace"
        ):
            _warn(logger, msg.external_params_ignored_warning_msg())
    else:
        errors.extend(_validate_external(config_data, logger, msg))

    # Validate GitLab HTTPS port
    gitlab_port = config_data.get("gitlab_https_port", 443)
    try:
        gitlab_port_int = int(gitlab_port)
        if not 1 <= gitlab_port_int <= 65535:
            errors.append(msg.invalid_gitlab_port_msg(gitlab_port))
    except (ValueError, TypeError):
        errors.append(msg.invalid_gitlab_port_msg(gitlab_port))

    # Log query defaults must stay within the configured tail ceiling
    tail_default = config_data.get("log_tail_lines_default", 50)
    tail_max = config_data.get("log_tail_lines_max", 10000)
    if (
        isinstance(tail_default, int) and isinstance(tail_max, int)
        and tail_default > tail_max
    ):
        errors.append(msg.log_tail_default_exceeds_max_msg(tail_default, tail_max))

    preview = config_data.get("log_ci_preview_lines", 50)
    if isinstance(preview, int) and isinstance(tail_max, int) and preview > tail_max:
        errors.append(msg.log_ci_preview_exceeds_max_msg(preview, tail_max))

    # Warn if BSM and GitLab on same host
    if gitlab_mode == "self_hosted" and host_ip and gitlab_host and str(host_ip).strip() == str(gitlab_host).strip():
        warning = msg.same_host_warning_msg()
        if logger:
            logger.warning(warning)

    return errors


def _is_set(config_data, key) -> bool:
    """True when *key* holds a non-blank value."""
    value = config_data.get(key)
    return value is not None and bool(str(value).strip())


def _warn(logger, text) -> None:
    """Log a warning when a logger is available."""
    if logger:
        logger.warning(text)


def _validate_external(config_data, logger, msg) -> List[str]:
    """Offline checks for gitlab_mode: external (connectivity is probed at execute time)."""
    # pylint: disable=C0415
    from ansible.module_utils.external_gitlab.ca_cert import validate_pem_bundle
    from ansible.module_utils.external_gitlab.url_checks import (
        is_valid_external_url,
        is_valid_namespace,
    )

    errors = []
    url = str(config_data.get("gitlab_external_url") or "").strip()
    if not url:
        errors.append(msg.missing_external_param_msg("gitlab_external_url"))
    elif not is_valid_external_url(url):
        errors.append(msg.invalid_external_url_msg(url))

    namespace = str(config_data.get("gitlab_project_namespace") or "").strip()
    if not namespace:
        errors.append(msg.missing_external_param_msg("gitlab_project_namespace"))
    elif not is_valid_namespace(namespace):
        errors.append(msg.invalid_project_namespace_msg(namespace))

    if _is_set(config_data, "gitlab_host"):
        _warn(logger, msg.gitlab_host_ignored_warning_msg())

    ca_path = str(config_data.get("gitlab_ca_cert_path") or "").strip()
    if ca_path:
        detail = validate_pem_bundle(ca_path)
        if detail:
            errors.append(msg.ca_cert_error_msg(detail))
    return errors
