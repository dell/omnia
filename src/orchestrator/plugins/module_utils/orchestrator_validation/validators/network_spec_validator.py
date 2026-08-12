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
L2 (semantic) validator for network_spec.yml.

The ``validate()`` entry point checks Networks structure, admin_network
presence, IP validity, and netmask bits.
"""

from ..core.validation_engine import is_valid_ipv4
from ..messages.orchestrator_messages import (
    NETWORK_SPEC_EMPTY_MSG,
    NETWORK_SPEC_NETWORKS_REQUIRED_MSG,
    NETWORK_SPEC_ADMIN_IP_INVALID_MSG,
    NETWORK_SPEC_NETMASK_REQUIRED_MSG,
    NETWORK_SPEC_ADMIN_REQUIRED_MSG,
)


def validate(ns_data, errors, logger=None):
    """
    L2 validation for network_spec.yml.

    Args:
        ns_data (dict): Parsed network_spec.yml content.
        errors (list): Mutable list to append error messages to.
        logger: Optional logger instance.
    """
    if not ns_data or not isinstance(ns_data, dict):
        errors.append(NETWORK_SPEC_EMPTY_MSG)
        if logger:
            logger.error(NETWORK_SPEC_EMPTY_MSG)
        return

    networks = ns_data.get("Networks")
    if not networks or not isinstance(networks, list):
        errors.append(NETWORK_SPEC_NETWORKS_REQUIRED_MSG)
        if logger:
            logger.error(NETWORK_SPEC_NETWORKS_REQUIRED_MSG)
        return

    has_admin = False
    for net in networks:
        if "admin_network" in net and isinstance(net["admin_network"], dict):
            has_admin = True
            an = net["admin_network"]
            oim_ip = an.get("primary_oim_admin_ip", "")
            if not oim_ip or not is_valid_ipv4(oim_ip):
                msg = NETWORK_SPEC_ADMIN_IP_INVALID_MSG.format(oim_ip)
                errors.append(msg)
                if logger:
                    logger.error(msg)
            bits = an.get("netmask_bits")
            if bits is None:
                errors.append(NETWORK_SPEC_NETMASK_REQUIRED_MSG)
                if logger:
                    logger.error(NETWORK_SPEC_NETMASK_REQUIRED_MSG)
            break

    if not has_admin:
        errors.append(NETWORK_SPEC_ADMIN_REQUIRED_MSG)
        if logger:
            logger.error(NETWORK_SPEC_ADMIN_REQUIRED_MSG)
