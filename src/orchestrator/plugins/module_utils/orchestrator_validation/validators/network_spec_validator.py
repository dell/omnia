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
"""L2 semantic validation for Orchestrator network specifications."""

from __future__ import annotations

import ipaddress
from logging import Logger
from typing import Any

from ..messages import orchestrator_messages as msg

AddressRange = tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]
ConfiguredNetwork = tuple[str, ipaddress.IPv4Network]
ConfiguredRange = tuple[str, AddressRange]


def record_error(errors: list[str], logger: Logger | None, message: str) -> None:
    """Append and optionally log one validation error."""
    errors.append(message)
    if logger:
        logger.error(message)


def is_valid_ipv4(address: Any) -> bool:
    """Return whether a value represents an IPv4 address."""
    try:
        return ipaddress.ip_address(address).version == 4
    except (TypeError, ValueError):
        return False


def network_from_config(config: dict[str, Any]) -> ipaddress.IPv4Network | None:
    """Return the strict IPv4 network declared by a network entry."""
    try:
        network = ipaddress.ip_network(
            f"{config.get('subnet', '')}/{config.get('netmask_bits', '')}",
            strict=True,
        )
    except (TypeError, ValueError):
        return None
    return network if isinstance(network, ipaddress.IPv4Network) else None


def _address_range(value: Any) -> AddressRange | None:
    """Return ordered IPv4 range endpoints or None for an invalid range."""
    try:
        start_text, end_text = value.split("-", 1)
        start = ipaddress.ip_address(start_text)
        end = ipaddress.ip_address(end_text)
    except (AttributeError, ValueError):
        return None
    if not isinstance(start, ipaddress.IPv4Address):
        return None
    if not isinstance(end, ipaddress.IPv4Address) or start > end:
        return None
    return start, end


def _validate_network_entry(
    config: Any,
    label: str,
    errors: list[str],
    logger: Logger | None,
) -> tuple[ipaddress.IPv4Network | None, AddressRange | None]:
    """Validate subnet, router, and DHCP-range relationships for one entry."""
    if not isinstance(config, dict):
        record_error(errors, logger, msg.network_entry_type_msg(label))
        return None, None

    network = network_from_config(config)
    if network is None:
        record_error(errors, logger, msg.network_definition_invalid_msg(label))
        return None, None

    router = config.get("router", "")
    try:
        router_in_network = ipaddress.ip_address(router) in network
    except (TypeError, ValueError):
        router_in_network = False
    if not router_in_network:
        record_error(
            errors,
            logger,
            msg.router_outside_network_msg(label, str(router), str(network)),
        )

    dhcp_range = _address_range(config.get("dynamic_range", ""))
    if dhcp_range is None:
        record_error(errors, logger, msg.dynamic_range_invalid_msg(label))
    elif not all(address in network for address in dhcp_range):
        record_error(
            errors,
            logger,
            msg.dynamic_range_outside_network_msg(label, str(network)),
        )

    return network, dhcp_range


def _validate_admin_ip(
    admin_config: dict[str, Any],
    network: ipaddress.IPv4Network | None,
    dhcp_range: AddressRange | None,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate the primary OIM admin IP against its network and DHCP range."""
    admin_ip = admin_config.get("primary_oim_admin_ip", "")
    if not is_valid_ipv4(admin_ip):
        record_error(errors, logger, msg.admin_ip_invalid_msg(str(admin_ip)))
        return

    parsed_admin_ip = ipaddress.ip_address(admin_ip)
    if network and parsed_admin_ip not in network:
        record_error(
            errors,
            logger,
            msg.admin_ip_outside_network_msg(str(admin_ip), str(network)),
        )
    if dhcp_range and dhcp_range[0] <= parsed_admin_ip <= dhcp_range[1]:
        record_error(errors, logger, msg.admin_ip_in_dynamic_range_msg())


def _validate_additional_subnets(
    admin_config: dict[str, Any],
    label: str,
    errors: list[str],
    logger: Logger | None,
) -> tuple[list[ConfiguredNetwork], list[ConfiguredRange]]:
    """Validate and return every additional subnet under an admin entry."""
    configured_networks: list[ConfiguredNetwork] = []
    configured_ranges: list[ConfiguredRange] = []
    additional_subnets = admin_config.get("additional_subnets", [])
    if not isinstance(additional_subnets, list):
        return configured_networks, configured_ranges

    for index, additional in enumerate(additional_subnets):
        subnet_label = f"{label}.additional_subnets[{index}]"
        additional_network, additional_range = _validate_network_entry(
            additional, subnet_label, errors, logger
        )
        if additional_network:
            configured_networks.append((subnet_label, additional_network))
        if additional_range:
            configured_ranges.append((subnet_label, additional_range))
    return configured_networks, configured_ranges


def _ranges_overlap(first: AddressRange, second: AddressRange) -> bool:
    """Return whether two inclusive IPv4 ranges intersect."""
    return first[0] <= second[1] and second[0] <= first[1]


def _validate_admin_overlaps(
    configured_networks: list[ConfiguredNetwork],
    configured_ranges: list[ConfiguredRange],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Reject subnet and DHCP-range overlaps across all admin entries."""
    for index, (label, network) in enumerate(configured_networks):
        if any(
            network.overlaps(previous_network)
            for _, previous_network in configured_networks[:index]
        ):
            record_error(errors, logger, msg.subnet_overlap_msg(label))

    for index, (label, address_range) in enumerate(configured_ranges):
        if any(
            _ranges_overlap(address_range, previous_range)
            for _, previous_range in configured_ranges[:index]
        ):
            record_error(errors, logger, msg.dynamic_range_overlap_msg(label))


def _validate_admin_bmc_relationships(
    admin_entries: list[tuple[str, dict[str, Any]]],
    configured_ranges: list[ConfiguredRange],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate OIM BMC addresses against admin IPs and every DHCP pool."""
    admin_addresses = {
        str(admin_config.get("primary_oim_admin_ip"))
        for _, admin_config in admin_entries
        if is_valid_ipv4(admin_config.get("primary_oim_admin_ip"))
    }
    for label, admin_config in admin_entries:
        bmc_ip = admin_config.get("primary_oim_bmc_ip", "")
        if not bmc_ip or not is_valid_ipv4(bmc_ip):
            continue

        parsed_bmc_ip = ipaddress.ip_address(bmc_ip)
        if str(parsed_bmc_ip) in admin_addresses:
            record_error(
                errors,
                logger,
                msg.admin_bmc_ip_same_msg(label, str(bmc_ip)),
            )

        for range_label, address_range in configured_ranges:
            if address_range[0] <= parsed_bmc_ip <= address_range[1]:
                record_error(
                    errors,
                    logger,
                    msg.bmc_ip_in_dynamic_range_msg(
                        label, str(bmc_ip), range_label
                    ),
                )


def _validate_ib_admin_relationships(
    all_admin_networks: list[ConfiguredNetwork],
    ib_networks: list[ConfiguredNetwork],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate that IB and admin subnets do not overlap."""
    for ib_label, ib_network in ib_networks:
        for admin_label, admin_network in all_admin_networks:
            if ib_network.overlaps(admin_network):
                record_error(
                    errors,
                    logger,
                    msg.ib_admin_subnet_overlap_msg(
                        ib_label,
                        str(ib_network),
                        admin_label,
                        str(admin_network),
                    ),
                )


def validate(config_data: Any, logger: Logger | None = None) -> list[str]:
    """Validate the complete L2 network specification contract.

    Args:
        config_data: Parsed ``network_spec.yml`` data.
        logger: Optional validation logger.

    Returns:
        Validation error messages, or an empty list for valid input.
    """
    errors: list[str] = []
    if not isinstance(config_data, dict) or not config_data:
        record_error(errors, logger, msg.NETWORK_SPEC_EMPTY_MSG)
        return errors

    networks = config_data.get("Networks")
    if not isinstance(networks, list) or not networks:
        record_error(errors, logger, msg.NETWORK_SPEC_NETWORKS_REQUIRED_MSG)
        return errors

    admin_entries: list[tuple[str, dict[str, Any]]] = []
    all_admin_networks: list[ConfiguredNetwork] = []
    configured_ranges: list[ConfiguredRange] = []
    ib_networks: list[ConfiguredNetwork] = []

    for index, entry in enumerate(networks):
        if not isinstance(entry, dict):
            continue

        admin_config = entry.get("admin_network")
        if isinstance(admin_config, dict):
            admin_label = f"Networks[{index}].admin_network"
            admin_entries.append((admin_label, admin_config))
            primary_network, primary_range = _validate_network_entry(
                admin_config, admin_label, errors, logger
            )
            if admin_config.get("netmask_bits") is None:
                record_error(
                    errors, logger, msg.NETWORK_SPEC_NETMASK_REQUIRED_MSG
                )
            _validate_admin_ip(
                admin_config, primary_network, primary_range, errors, logger
            )
            if primary_network:
                primary_entry = (admin_label, primary_network)
                all_admin_networks.append(primary_entry)
            if primary_range:
                configured_ranges.append((admin_label, primary_range))
            additional_networks, additional_ranges = (
                _validate_additional_subnets(
                    admin_config, admin_label, errors, logger
                )
            )
            all_admin_networks.extend(additional_networks)
            configured_ranges.extend(additional_ranges)

        ib_config = entry.get("ib_network")
        if isinstance(ib_config, dict):
            ib_label = f"Networks[{index}].ib_network"
            ib_network = network_from_config(ib_config)
            if ib_network is None:
                record_error(
                    errors,
                    logger,
                    msg.network_definition_invalid_msg(ib_label),
                )
            else:
                ib_networks.append((ib_label, ib_network))

    if not admin_entries:
        record_error(errors, logger, msg.NETWORK_SPEC_ADMIN_REQUIRED_MSG)
        return errors

    _validate_admin_overlaps(
        all_admin_networks, configured_ranges, errors, logger
    )
    _validate_admin_bmc_relationships(
        admin_entries, configured_ranges, errors, logger
    )
    _validate_ib_admin_relationships(
        all_admin_networks,
        ib_networks,
        errors,
        logger,
    )
    return errors
