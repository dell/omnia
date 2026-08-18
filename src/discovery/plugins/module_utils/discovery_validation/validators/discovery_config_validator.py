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
L2 (semantic) validator for discovery_config.yml.

The ``validate()`` entry point runs all cross-field and semantic checks.
"""

import ipaddress

from ..messages.discovery_messages import (
    OME_IP_REQUIRED_MSG,
    OME_IP_LOOPBACK_MSG,
    OME_IP_INVALID_MSG,
)


def _validate_ome_ip(config_data, errors, logger=None):
    """
    Validate OME IP address logic.

    Rules:
    - If enable_bmc_discovery is true, ome_ip must be a valid, non-loopback IPv4.
    - If enable_bmc_discovery is false, ome_ip is ignored.
    """
    enable_bmc = config_data.get("enable_bmc_discovery", False)
    if not enable_bmc:
        return

    ome_ip = config_data.get("ome_ip", "")
    if not ome_ip:
        errors.append(OME_IP_REQUIRED_MSG)
        if logger:
            logger.error(OME_IP_REQUIRED_MSG)
        return

    try:
        addr = ipaddress.ip_address(ome_ip)
        if addr.is_loopback:
            msg = OME_IP_LOOPBACK_MSG.format(ome_ip)
            errors.append(msg)
            if logger:
                logger.error(msg)
    except ValueError:
        msg = OME_IP_INVALID_MSG.format(ome_ip)
        errors.append(msg)
        if logger:
            logger.error(msg)


def validate(config_data, errors, logger=None):
    """
    Run all L2 validators for discovery_config.yml.

    Args:
        config_data (dict): Parsed discovery_config.yml content.
        errors (list): Mutable list to append error messages to.
        logger: Optional logger instance.
    """
    _validate_ome_ip(config_data, errors, logger)
