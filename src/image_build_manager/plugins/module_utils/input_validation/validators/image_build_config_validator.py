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
Image build configuration validator.

This module validates image_build_config.yml for:
- S3 provider/endpoint consistency
- aarch64 build host dependencies
- Async job timing constraints
- Functional groups source/list consistency
- Build concurrency settings
"""
from ansible.module_utils.input_validation.messages import (  # pylint: disable=E0401
    image_build_messages as msg,
)


def _validate_s3_config(config_data, errors, logger=None):
    """
    Validate S3 configuration logic.

    Rules:
    - If provider is 'powerscale', endpoint_url is required and must not be empty.
    - If provider is 'minio', endpoint_url should not be set (auto-managed).
    """
    s3 = config_data.get("s3_configurations", {})
    provider = s3.get("provider", "")
    endpoint_url = s3.get("endpoint_url", "")

    if provider == "powerscale":
        if not endpoint_url or not endpoint_url.strip():
            errors.append(msg.S3_ENDPOINT_REQUIRED_POWERSCALE_MSG)
            if logger:
                logger.error(msg.S3_ENDPOINT_REQUIRED_POWERSCALE_MSG)

    if provider == "minio" and endpoint_url:
        if logger:
            logger.warning(msg.S3_ENDPOINT_NOT_SET_MINIO_MSG)


def _validate_aarch64_config(config_data, errors, logger=None):
    """
    Validate aarch64 build configuration logic.

    Rules:
    - If aarch64_inventory_host_ip is set, aarch64_ssh_user must also be set.
    - aarch64_inventory_host_ip format is already validated by L1 schema regex.
    """
    host_ip = config_data.get("aarch64_inventory_host_ip", "")
    ssh_user = config_data.get("aarch64_ssh_user", "")

    if host_ip and not ssh_user:
        errors.append(msg.AARCH64_SSH_USER_REQUIRED_MSG)
        if logger:
            logger.error(msg.AARCH64_SSH_USER_REQUIRED_MSG)


def _validate_build_image_settings(config_data, errors, logger=None):
    """
    Validate build_image async job settings logic.

    Rules:
    - job_async must be > job_retry * job_delay (otherwise async times out before retries finish).
    """
    build_image = config_data.get("build_image", {})
    if not build_image:
        return

    job_async = build_image.get("job_async", 7200)
    job_retry = build_image.get("job_retry", 240)
    job_delay = build_image.get("job_delay", 30)

    if job_async < job_retry * job_delay:
        error = msg.job_async_too_low_msg(job_async, job_retry, job_delay)
        errors.append(error)
        if logger:
            logger.error(error)


def _validate_functional_groups_source(config_data, errors, logger=None):
    """
    Validate functional_groups_source value.

    Rules:
    - functional_groups_source must be 'config' or 'catalog'.
    - In config mode, groups are derived from package_groups.yml keys (not from image_build_config.yml).
    - In catalog mode, groups are auto-detected from catalog layers.
    - The deprecated functional_groups[] list in image_build_config.yml is ignored.
    """
    source = config_data.get("functional_groups_source", "config")

    if source not in ("config", "catalog"):
        error = f"Invalid functional_groups_source: '{source}'. Must be 'config' or 'catalog'."
        errors.append(error)
        if logger:
            logger.error(error)

    fg_list = config_data.get("functional_groups", [])
    if fg_list and logger:
        logger.warning(
            "functional_groups[] in image_build_config.yml is deprecated and ignored. "
            "Groups are derived from package_groups.yml keys (config mode) or catalog layers (catalog mode)."
        )


def _validate_build_concurrency(config_data, errors, logger=None):
    """
    Validate build concurrency settings.

    Rules:
    - max_parallel must be 0 (unlimited) or a positive integer.
    """
    build_image = config_data.get("build_image", {})
    if not build_image:
        return

    max_parallel = build_image.get("max_parallel", 0)
    if not isinstance(max_parallel, int) or max_parallel < 0:
        errors.append(msg.MAX_PARALLEL_INVALID_MSG)
        if logger:
            logger.error(msg.MAX_PARALLEL_INVALID_MSG)


def validate(config_data, logger=None):
    """
    Run all L2 validation rules on image_build_config.yml data.

    Args:
        config_data (dict): Parsed image_build_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []
    _validate_s3_config(config_data, errors, logger)
    _validate_aarch64_config(config_data, errors, logger)
    _validate_build_image_settings(config_data, errors, logger)
    _validate_functional_groups_source(config_data, errors, logger)
    _validate_build_concurrency(config_data, errors, logger)
    return errors
