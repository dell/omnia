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
L2 (semantic) validators for orchestrator_config.yml.

Each function validates a specific aspect and appends errors to the list.
The ``validate()`` entry point runs all checks.
"""

import os
import re

from ..core.validation_engine import read_csv_rows, col_index, is_valid_ipv4
from ..messages.orchestrator_messages import (
    LANGUAGE_REQUIRED_MSG,
    LANGUAGE_UNSUPPORTED_MSG,
    LEASE_TIME_INVALID_MSG,
    KERNEL_VERSION_FORMAT_MSG,
    S3_ENDPOINT_REQUIRED_MSG,
    S3_ENDPOINT_NOT_NEEDED_MSG,
    CLOUD_INIT_FILE_MISSING_MSG,
    PXE_MAPPING_REQUIRED_MSG,
    PXE_MAPPING_NOT_FOUND_MSG,
    PXE_MAPPING_READ_FAILED_MSG,
    PXE_MAPPING_MISSING_COLUMNS_MSG,
    PXE_MAPPING_DUP_SERVICE_TAG_MSG,
    PXE_MAPPING_DUP_HOSTNAME_MSG,
    PXE_MAPPING_DUP_ADMIN_IP_MSG,
    PXE_MAPPING_INVALID_IP_MSG,
)

REQUIRED_HEADERS = [
    "FUNCTIONAL_GROUP_NAME", "GROUP_NAME", "SERVICE_TAG",
    "PARENT_SERVICE_TAG", "HOSTNAME", "ADMIN_MAC", "ADMIN_IP",
    "BMC_MAC", "BMC_IP",
]


def _validate_language(config_data, errors, logger=None):
    """language must be set and must contain 'en_US.UTF-8'."""
    language = config_data.get("language", "")
    if not language:
        errors.append(LANGUAGE_REQUIRED_MSG)
        if logger:
            logger.error(LANGUAGE_REQUIRED_MSG)
    elif "en_US.UTF-8" not in language:
        msg = LANGUAGE_UNSUPPORTED_MSG.format(language)
        errors.append(msg)
        if logger:
            logger.error(msg)


def _validate_default_lease_time(config_data, errors, logger=None):
    """default_lease_time must be a positive integer."""
    dlt = config_data.get("default_lease_time", "")
    try:
        val = int(dlt)
        if val <= 0:
            raise ValueError("non-positive")
    except (TypeError, ValueError):
        msg = LEASE_TIME_INVALID_MSG.format(dlt)
        errors.append(msg)
        if logger:
            logger.error(msg)


def _validate_kernel_version_override(config_data, errors, logger=None):
    """If set, kernel_version_override must match X.Y.Z-suffix format."""
    kvo = config_data.get("kernel_version_override", "")
    if kvo and not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+-.+$", kvo):
        msg = KERNEL_VERSION_FORMAT_MSG.format(kvo)
        errors.append(msg)
        if logger:
            logger.error(msg)


def _validate_s3_config(config_data, errors, logger=None):
    """Validate s3_storage_provider / s3_endpoint consistency."""
    provider = config_data.get("s3_storage_provider", "minio")
    endpoint = config_data.get("s3_endpoint", "")
    if provider in ("powerscale", "external"):
        if not endpoint or not endpoint.strip():
            msg = S3_ENDPOINT_REQUIRED_MSG.format(provider)
            errors.append(msg)
            if logger:
                logger.error(msg)
    if provider == "minio" and endpoint:
        if logger:
            logger.warning(S3_ENDPOINT_NOT_NEEDED_MSG)


def _validate_additional_cloud_init_config(config_data, errors, logger=None):
    """If additional_cloud_init_config_file is set, the file must exist."""
    aci_path = config_data.get("additional_cloud_init_config_file", "")
    if aci_path and not os.path.isfile(aci_path):
        msg = CLOUD_INIT_FILE_MISSING_MSG.format(aci_path)
        errors.append(msg)
        if logger:
            logger.error(msg)


def _validate_pxe_mapping_file(config_data, errors, logger=None):
    """Validate pxe_mapping_file_path: existence, headers, duplicates, IPs."""
    path = config_data.get("pxe_mapping_file_path", "")
    if not path:
        errors.append(PXE_MAPPING_REQUIRED_MSG)
        if logger:
            logger.error(PXE_MAPPING_REQUIRED_MSG)
        return

    if not os.path.isfile(path):
        msg = PXE_MAPPING_NOT_FOUND_MSG.format(path)
        errors.append(msg)
        if logger:
            logger.error(msg)
        return

    try:
        header, rows = read_csv_rows(path)
    except Exception as e:
        msg = PXE_MAPPING_READ_FAILED_MSG.format(path, e)
        errors.append(msg)
        if logger:
            logger.error(msg)
        return

    missing = [h for h in REQUIRED_HEADERS if h not in header]
    if missing:
        msg = PXE_MAPPING_MISSING_COLUMNS_MSG.format(path, missing)
        errors.append(msg)
        if logger:
            logger.error(msg)
        return

    st_idx = col_index(header, "SERVICE_TAG")
    hn_idx = col_index(header, "HOSTNAME")
    aip_idx = col_index(header, "ADMIN_IP")

    service_tags = [r[st_idx] for r in rows if r[st_idx]]
    hostnames = [r[hn_idx] for r in rows if r[hn_idx]]
    admin_ips = [r[aip_idx] for r in rows if r[aip_idx]]

    dup_st = [st for st in set(service_tags) if service_tags.count(st) > 1]
    if dup_st:
        msg = PXE_MAPPING_DUP_SERVICE_TAG_MSG.format(dup_st)
        errors.append(msg)
        if logger:
            logger.error(msg)

    dup_hn = [h for h in set(hostnames) if hostnames.count(h) > 1]
    if dup_hn:
        msg = PXE_MAPPING_DUP_HOSTNAME_MSG.format(dup_hn)
        errors.append(msg)
        if logger:
            logger.error(msg)

    dup_ip = [ip for ip in set(admin_ips) if admin_ips.count(ip) > 1]
    if dup_ip:
        msg = PXE_MAPPING_DUP_ADMIN_IP_MSG.format(dup_ip)
        errors.append(msg)
        if logger:
            logger.error(msg)

    for ip in admin_ips:
        if not is_valid_ipv4(ip):
            msg = PXE_MAPPING_INVALID_IP_MSG.format(ip)
            errors.append(msg)
            if logger:
                logger.error(msg)


def validate(config_data, errors, logger=None):
    """
    Run all L2 validators for orchestrator_config.yml.

    Args:
        config_data (dict): Parsed orchestrator_config.yml content.
        errors (list): Mutable list to append error messages to.
        logger: Optional logger instance.
    """
    _validate_language(config_data, errors, logger)
    _validate_default_lease_time(config_data, errors, logger)
    _validate_kernel_version_override(config_data, errors, logger)
    _validate_s3_config(config_data, errors, logger)
    _validate_additional_cloud_init_config(config_data, errors, logger)
    _validate_pxe_mapping_file(config_data, errors, logger)
