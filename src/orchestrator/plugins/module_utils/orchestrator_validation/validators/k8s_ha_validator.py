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
"""L2 semantic validation for Kubernetes service-node high availability.

``enable_k8s_ha`` and ``virtual_ip_address`` live on the ``service_k8s_cluster``
entry in ``omnia_config.yml`` that they qualify. The former
``high_availability_config.yml``, its ``cluster_name`` join back to
``omnia_config.yml``, and the mismatch error class that join produced have all
been removed. What remains here is the genuine network validation the join
logic was wrapped around: the virtual IP must not collide with a mapped node,
a DHCP range, an OIM address, or the external pool, and it must sit in the
control-plane subnet.
"""

from __future__ import annotations

import ipaddress
from logging import Logger
from typing import Any

from ..messages import orchestrator_messages as msg
from .network_spec_validator import record_error
from .omnia_config_validator import (
    AddressRange,
    load_project_yaml,
    load_pxe_mapping_rows,
    parse_ipv4_range_or_cidr,
    selected_workloads,
)


def _network_from_entry(entry: Any) -> ipaddress.IPv4Network | None:
    """Return an IPv4 network declared by an admin-network entry."""
    if not isinstance(entry, dict):
        return None
    try:
        network = ipaddress.ip_network(
            f"{entry.get('subnet', '')}/{entry.get('netmask_bits', '')}",
            strict=False,
        )
    except (TypeError, ValueError):
        return None
    return network if isinstance(network, ipaddress.IPv4Network) else None


def _network_context(
    input_project_dir: str,
) -> tuple[
    list[ipaddress.IPv4Network],
    list[AddressRange],
    dict[str, set[str]],
]:
    """Load all admin subnets, DHCP pools, and fixed OIM addresses."""
    data = load_project_yaml(input_project_dir, "network_spec.yml")
    admin_networks: list[ipaddress.IPv4Network] = []
    dhcp_ranges: list[AddressRange] = []
    oim_addresses: dict[str, set[str]] = {
        "primary_oim_admin_ip": set(),
        "primary_oim_bmc_ip": set(),
    }
    if not isinstance(data, dict) or not isinstance(data.get("Networks"), list):
        return admin_networks, dhcp_ranges, oim_addresses

    for network_item in data["Networks"]:
        if not isinstance(network_item, dict):
            continue
        admin_entry = network_item.get("admin_network")
        if not isinstance(admin_entry, dict):
            continue
        primary_network = _network_from_entry(admin_entry)
        if primary_network and primary_network not in admin_networks:
            admin_networks.append(primary_network)
        primary_range = parse_ipv4_range_or_cidr(
            admin_entry.get("dynamic_range")
        )
        if primary_range:
            dhcp_ranges.append(primary_range)
        for field in oim_addresses:
            value = admin_entry.get(field)
            try:
                address = ipaddress.ip_address(value)
            except (TypeError, ValueError):
                continue
            if isinstance(address, ipaddress.IPv4Address):
                oim_addresses[field].add(str(address))

        additional_subnets = admin_entry.get("additional_subnets", [])
        if not isinstance(additional_subnets, list):
            continue
        for additional in additional_subnets:
            additional_network = _network_from_entry(additional)
            if additional_network and additional_network not in admin_networks:
                admin_networks.append(additional_network)
            if isinstance(additional, dict):
                additional_range = parse_ipv4_range_or_cidr(
                    additional.get("dynamic_range")
                )
                if additional_range:
                    dhcp_ranges.append(additional_range)
    return admin_networks, dhcp_ranges, oim_addresses


def _mapped_addresses(
    rows: list[dict[str, str]],
) -> dict[str, set[str]]:
    """Return all valid node addresses grouped by PXE mapping column."""
    mapped: dict[str, set[str]] = {
        "ADMIN_IP": set(),
        "BMC_IP": set(),
        "IB_IP": set(),
    }
    for row in rows:
        for field in mapped:
            try:
                address = ipaddress.ip_address(row.get(field, ""))
            except (TypeError, ValueError):
                continue
            if isinstance(address, ipaddress.IPv4Address):
                mapped[field].add(str(address))
    return mapped


def _control_plane_network(
    mapping_rows: list[dict[str, str]],
    admin_networks: list[ipaddress.IPv4Network],
    errors: list[str],
    logger: Logger | None,
) -> ipaddress.IPv4Network | None:
    """Resolve the single admin subnet containing all control-plane nodes."""
    control_plane_addresses: list[ipaddress.IPv4Address] = []
    for row in mapping_rows:
        if not row.get("FUNCTIONAL_GROUP_NAME", "").startswith(
            "service_kube_control_plane"
        ):
            continue
        try:
            address = ipaddress.ip_address(row.get("ADMIN_IP", ""))
        except (TypeError, ValueError):
            continue
        if isinstance(address, ipaddress.IPv4Address):
            control_plane_addresses.append(address)

    if not control_plane_addresses:
        record_error(errors, logger, msg.HA_CONTROL_PLANE_REQUIRED_MSG)
        return None

    matched_networks: set[ipaddress.IPv4Network] = set()
    unmatched_addresses: list[str] = []
    for address in control_plane_addresses:
        matches = [network for network in admin_networks if address in network]
        if len(matches) != 1:
            unmatched_addresses.append(str(address))
        else:
            matched_networks.add(matches[0])
    if unmatched_addresses:
        record_error(
            errors,
            logger,
            msg.ha_control_plane_network_unresolved_msg(
                sorted(unmatched_addresses)
            ),
        )
        return None
    if len(matched_networks) != 1:
        record_error(
            errors,
            logger,
            msg.ha_control_plane_multiple_subnets_msg(
                sorted(str(network) for network in matched_networks)
            ),
        )
        return None
    return next(iter(matched_networks))


def _validate_vip_conflicts(
    vip: ipaddress.IPv4Address,
    external_pool: Any,
    mapping_rows: list[dict[str, str]],
    dhcp_ranges: list[AddressRange],
    oim_addresses: dict[str, set[str]],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Reject VIP collisions with OIM, node, DHCP, and MetalLB addresses."""
    vip_text = str(vip)
    for field, addresses in oim_addresses.items():
        if vip_text in addresses:
            record_error(
                errors,
                logger,
                msg.ha_vip_address_conflict_msg(vip_text, field),
            )
    for field, addresses in _mapped_addresses(mapping_rows).items():
        if vip_text in addresses:
            record_error(
                errors,
                logger,
                msg.ha_vip_address_conflict_msg(vip_text, field),
            )

    matching_dhcp = [
        f"{address_range[0]}-{address_range[1]}"
        for address_range in dhcp_ranges
        if address_range[0] <= vip <= address_range[1]
    ]
    if matching_dhcp:
        record_error(
            errors,
            logger,
            msg.ha_vip_dhcp_conflict_msg(vip_text, matching_dhcp),
        )

    parsed_external = parse_ipv4_range_or_cidr(external_pool)
    if parsed_external and parsed_external[0] <= vip <= parsed_external[1]:
        record_error(
            errors,
            logger,
            msg.ha_vip_external_pool_conflict_msg(
                vip_text, str(external_pool)
            ),
        )


def _validate_subnet_compatibility(
    vip: ipaddress.IPv4Address,
    external_pool: Any,
    control_plane_network: ipaddress.IPv4Network,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate kube-vip and MetalLB pool placement on the control-plane L2."""
    if (
        vip not in control_plane_network
        or vip == control_plane_network.network_address
        or vip == control_plane_network.broadcast_address
    ):
        record_error(
            errors,
            logger,
            msg.ha_vip_control_plane_subnet_msg(
                str(vip), str(control_plane_network)
            ),
        )

    parsed_external = parse_ipv4_range_or_cidr(external_pool)
    if parsed_external and not all(
        address in control_plane_network for address in parsed_external
    ):
        record_error(
            errors,
            logger,
            msg.ha_external_pool_control_plane_subnet_msg(
                str(external_pool), str(control_plane_network)
            ),
        )


def validate_deployed_cluster_ha(
    deployed_cluster: Any,
    input_project_dir: str,
    logger: Logger | None = None,
) -> list[str]:
    """Validate Kubernetes HA settings on the deployed ``service_k8s_cluster``.

    The HA parameters now live on the cluster entry they qualify, so there is
    no cluster_name join to reconcile and no mismatch error class. What remains
    is the genuine network validation: the virtual IP must not collide with a
    mapped node, a DHCP range, an OIM address, or the external pool, and it
    must sit in the control-plane subnet.

    Args:
        deployed_cluster: The ``service_k8s_cluster`` entry whose ``deployment``
            is true.
        input_project_dir: Current project input directory.
        logger: Optional validation logger.

    Returns:
        Validation error messages, or an empty list when the PXE mapping
        selects no Kubernetes workload.
    """
    errors: list[str] = []
    if not isinstance(deployed_cluster, dict):
        return errors

    mapping_rows = load_pxe_mapping_rows(input_project_dir)
    if "kubernetes" not in selected_workloads(mapping_rows):
        return errors

    # Required only when the mapping selects Kubernetes, so Slurm-only projects
    # that keep an unused deployed entry are unaffected. kube-vip and the
    # metadata templates always consume the VIP, so it is validated even when
    # enable_k8s_ha is false, matching the retired standalone input.
    if not isinstance(deployed_cluster.get("enable_k8s_ha"), bool):
        record_error(
            errors, logger, msg.ha_field_required_msg("enable_k8s_ha", "a boolean")
        )
    raw_vip = deployed_cluster.get("virtual_ip_address")
    if raw_vip is None or not str(raw_vip).strip():
        record_error(
            errors,
            logger,
            msg.ha_field_required_msg("virtual_ip_address", "an IPv4 address"),
        )
        return errors
    try:
        vip = ipaddress.ip_address(raw_vip)
    except (TypeError, ValueError):
        record_error(errors, logger, msg.ha_vip_invalid_msg(str(raw_vip or "")))
        return errors
    if not isinstance(vip, ipaddress.IPv4Address):
        record_error(errors, logger, msg.ha_vip_invalid_msg(str(raw_vip or "")))
        return errors

    admin_networks, dhcp_ranges, oim_addresses = _network_context(
        input_project_dir
    )
    external_pool = deployed_cluster.get("pod_external_ip_range")
    _validate_vip_conflicts(
        vip,
        external_pool,
        mapping_rows,
        dhcp_ranges,
        oim_addresses,
        errors,
        logger,
    )
    control_plane_network = _control_plane_network(
        mapping_rows, admin_networks, errors, logger
    )
    if control_plane_network:
        _validate_subnet_compatibility(
            vip,
            external_pool,
            control_plane_network,
            errors,
            logger,
        )
    return errors


def is_applicable(input_project_dir: str) -> bool:
    """Return whether the PXE mapping selects a Kubernetes workload."""
    mapping_rows = load_pxe_mapping_rows(input_project_dir)
    return "kubernetes" in selected_workloads(mapping_rows)
