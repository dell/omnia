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
Image build manager validation flow — L2 (logic) validation rules.

These are cross-field and semantic validations that go beyond JSON schema (L1).
They verify business-logic constraints specific to image_build_manager.
"""

import os


def validate_s3_config(config_data, errors, logger=None):
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
            msg = ("image_build_config: s3_configurations.endpoint_url is required "
                   "when provider is 'powerscale'.")
            errors.append(msg)
            if logger:
                logger.error(msg)

    if provider == "minio" and endpoint_url:
        msg = ("image_build_config: s3_configurations.endpoint_url should not be set "
               "when provider is 'minio' (auto-managed by deploy_minio role).")
        if logger:
            logger.warning(msg)


def validate_aarch64_config(config_data, errors, logger=None):
    """
    Validate aarch64 build configuration logic.

    Rules:
    - If aarch64_inventory_host_ip is set, aarch64_ssh_user must also be set.
    - aarch64_inventory_host_ip format is already validated by L1 schema regex.
    """
    host_ip = config_data.get("aarch64_inventory_host_ip", "")
    ssh_user = config_data.get("aarch64_ssh_user", "")

    if host_ip and not ssh_user:
        msg = ("image_build_config: aarch64_ssh_user is required when "
               "aarch64_inventory_host_ip is set.")
        errors.append(msg)
        if logger:
            logger.error(msg)


def validate_build_image_settings(config_data, errors, logger=None):
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
        msg = (f"image_build_config: build_image.job_async ({job_async}s) must be >= "
               f"job_retry * job_delay ({job_retry} * {job_delay} = {job_retry * job_delay}s). "
               "Otherwise the async timeout occurs before all retries complete.")
        errors.append(msg)
        if logger:
            logger.error(msg)


def validate_credentials_logic(cred_data, config_data, errors, logger=None):
    """
    Validate credential file logic against config.

    Rules:
    - If s3 provider is 'powerscale', s3_access_id must be present and non-empty.
    - s3_secret_key and provision_password are always required (enforced by L1 schema).
    """
    s3 = config_data.get("s3_configurations", {})
    provider = s3.get("provider", "")

    if provider == "powerscale":
        s3_access_id = cred_data.get("s3_access_id", "")
        if not s3_access_id or not s3_access_id.strip():
            msg = ("image_build_credentials: s3_access_id is required when "
                   "s3_configurations.provider is 'powerscale'.")
            errors.append(msg)
            if logger:
                logger.error(msg)


def validate_image_build_config(config_data, logger=None):
    """
    Run all L2 validation rules on image_build_config.yml data.

    Args:
        config_data (dict): Parsed image_build_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []
    validate_s3_config(config_data, errors, logger)
    validate_aarch64_config(config_data, errors, logger)
    validate_build_image_settings(config_data, errors, logger)
    return errors
