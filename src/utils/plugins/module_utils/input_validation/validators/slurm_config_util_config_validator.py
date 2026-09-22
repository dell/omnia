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
Slurm Config Util configuration validator.

This module validates slurm_config_util_config.yml for:
- File path validation
- NFS export format validation
- Cleanup confirmation token validation
- Numeric validation for limits
"""
import os
import re
from ansible.module_utils.input_validation.messages import (  # pylint: disable=E0401
    utils_messages as msg,
)


def _validate_omnia_config_path(config_data, errors, logger=None):
    """
    Validate omnia_config_path configuration.

    Rules:
    - If provided, must be a valid file path format
    """
    omnia_config_path = config_data.get("omnia_config_path", "")
    if omnia_config_path and omnia_config_path.strip():
        # Basic path validation - should contain valid path characters
        if not re.match(r'^[/a-zA-Z0-9_\.\-]+$', omnia_config_path.strip()):
            errors.append(msg.OMNIA_CONFIG_PATH_INVALID_MSG)
            if logger:
                logger.error(msg.OMNIA_CONFIG_PATH_INVALID_MSG)


def _validate_storage_config_path(config_data, errors, logger=None):
    """
    Validate storage_config_path configuration.

    Rules:
    - If provided, must be a valid file path format
    """
    storage_config_path = config_data.get("storage_config_path", "")
    if storage_config_path and storage_config_path.strip():
        if not re.match(r'^[/a-zA-Z0-9_\.\-]+$', storage_config_path.strip()):
            errors.append(msg.STORAGE_CONFIG_PATH_INVALID_MSG)
            if logger:
                logger.error(msg.STORAGE_CONFIG_PATH_INVALID_MSG)


def _validate_pxe_mapping_path(config_data, errors, logger=None):
    """
    Validate pxe_mapping_path configuration.

    Rules:
    - If provided, must be a valid file path with .yaml or .csv extension
    """
    pxe_mapping_path = config_data.get("pxe_mapping_path", "")
    if pxe_mapping_path and pxe_mapping_path.strip():
        if not re.match(r'^[/a-zA-Z0-9_\.\-]+\.(yaml|csv)$', pxe_mapping_path.strip()):
            errors.append(msg.PXE_MAPPING_PATH_INVALID_MSG)
            if logger:
                logger.error(msg.PXE_MAPPING_PATH_INVALID_MSG)


def _validate_backup_path(config_data, errors, logger=None):
    """
    Validate backup_path configuration.

    Rules:
    - If provided, must be a valid local path or NFS export format (server:/path)
    """
    backup_path = config_data.get("backup_path", "")
    if backup_path and backup_path.strip():
        # Check for NFS export format (server:/path) or local path
        nfs_pattern = r'^[a-zA-Z0-9\.\-]+:/[/a-zA-Z0-9_\.\-]+$'
        local_path_pattern = r'^[/a-zA-Z0-9_\.\-]+$'
        
        if not (re.match(nfs_pattern, backup_path.strip()) or 
                re.match(local_path_pattern, backup_path.strip())):
            errors.append(msg.BACKUP_PATH_INVALID_MSG)
            if logger:
                logger.error(msg.BACKUP_PATH_INVALID_MSG)


def _validate_cleanup_confirm_token(config_data, errors, logger=None):
    """
    Validate slurm_cleanup_confirm_token configuration.

    Rules:
    - Must be 'YES' to proceed with destructive cleanup operations
    """
    confirm_token = config_data.get("slurm_cleanup_confirm_token", "")
    if confirm_token and confirm_token.strip() != "YES":
        errors.append(msg.CLEANUP_CONFIRM_TOKEN_INVALID_MSG)
        if logger:
            logger.error(msg.CLEANUP_CONFIRM_TOKEN_INVALID_MSG)


def _validate_rollback_limit(config_data, errors, logger=None):
    """
    Validate rollback_backup_list_limit configuration.

    Rules:
    - Must be a positive integer
    """
    rollback_limit = config_data.get("rollback_backup_list_limit", 20)
    if rollback_limit is not None:
        try:
            limit = int(rollback_limit)
            if limit <= 0:
                errors.append(msg.ROLLBACK_LIMIT_INVALID_MSG)
                if logger:
                    logger.error(msg.ROLLBACK_LIMIT_INVALID_MSG)
        except (ValueError, TypeError):
            errors.append(msg.ROLLBACK_LIMIT_INVALID_MSG)
            if logger:
                logger.error(msg.ROLLBACK_LIMIT_INVALID_MSG)


def validate(config_data, logger=None):
    """
    Run all L2 validation rules on slurm_config_util_config.yml data.

    Args:
        config_data (dict): Parsed slurm_config_util_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []
    _validate_omnia_config_path(config_data, errors, logger)
    _validate_storage_config_path(config_data, errors, logger)
    _validate_pxe_mapping_path(config_data, errors, logger)
    _validate_backup_path(config_data, errors, logger)
    _validate_cleanup_confirm_token(config_data, errors, logger)
    _validate_rollback_limit(config_data, errors, logger)
    return errors
