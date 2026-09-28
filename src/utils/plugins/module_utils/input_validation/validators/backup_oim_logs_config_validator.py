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
Backup OIM Logs configuration validator.

This module validates backup_oim_logs_config.yml for:
- Domain list validation
- Valid domain names
"""
from ansible.module_utils.input_validation.messages import (  # pylint: disable=E0401
    utils_messages as msg,
)

# Valid Omnia domains that can be backed up
VALID_OMNIA_DOMAINS = {
    "repo_manager",
    "image_build_manager",
    "orchestrator",
    "discovery",
    "telemetry",
    "build_stream",
    "utils",
}


def _validate_domains(config_data, errors, logger=None):
    """
    Validate domains list configuration.

    Rules:
    - domains list cannot be empty when specified
    - All domain names must be valid Omnia domains
    """
    domains = config_data.get("domains", [])
    
    if domains is not None and len(domains) == 0:
        errors.append(msg.DOMAINS_LIST_EMPTY_MSG)
        if logger:
            logger.error(msg.DOMAINS_LIST_EMPTY_MSG)
        return
    
    for domain in domains:
        if domain not in VALID_OMNIA_DOMAINS:
            error = msg.INVALID_DOMAIN_NAME_MSG.format(domain=domain)
            errors.append(error)
            if logger:
                logger.error(error)


def validate(config_data, logger=None):
    """
    Run all L2 validation rules on backup_oim_logs_config.yml data.

    Args:
        config_data (dict): Parsed backup_oim_logs_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []
    _validate_domains(config_data, errors, logger)
    return errors
