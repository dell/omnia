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
Discovery domain validation flow — L2 (logic) validation rules.

These are cross-field and semantic validations that go beyond JSON schema (L1).
They verify business-logic constraints specific to the discovery domain.
"""

import ipaddress


def validate_ome_ip_reachability(config_data, errors, logger=None):
    """
    Validate OME IP address logic.

    Rules:
    - If enable_bmc_discovery is true, ome_ip must be a valid, non-loopback IPv4 address.
    - If enable_bmc_discovery is false, ome_ip is ignored.
    """
    enable_bmc = config_data.get("enable_bmc_discovery", False)
    if not enable_bmc:
        return

    ome_ip = config_data.get("ome_ip", "")
    if not ome_ip:
        msg = "discovery_config: ome_ip is required when enable_bmc_discovery is true."
        errors.append(msg)
        if logger:
            logger.error(msg)
        return

    try:
        addr = ipaddress.ip_address(ome_ip)
        if addr.is_loopback:
            msg = (f"discovery_config: ome_ip '{ome_ip}' is a loopback address. "
                   "Provide the actual OME appliance IP.")
            errors.append(msg)
            if logger:
                logger.error(msg)
    except ValueError:
        msg = f"discovery_config: ome_ip '{ome_ip}' is not a valid IPv4 address."
        errors.append(msg)
        if logger:
            logger.error(msg)


def validate_discovery_config(config_data, logger=None):
    """
    Run all L2 validation rules on discovery_config.yml data.

    Args:
        config_data (dict): Parsed discovery_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []
    validate_ome_ip_reachability(config_data, errors, logger)
    return errors
