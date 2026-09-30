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

# pylint: disable=too-few-public-methods,too-many-locals,too-many-statements
"""Resolve stable Omnia node identities from SMD Hardware Inventory."""

import contextlib
import fcntl
import ipaddress
import os
import re
import stat
from collections.abc import Iterable
from typing import Any

XNAME_RE = re.compile(r"^x1000c(?P<c>[0-9]+)s(?P<s>[0-9])b(?P<b>[0-9])n0$")
MAC_RE = re.compile(r"^[0-9a-f]{12}$")
SERVICE_TAG_RE = re.compile(r"^[A-Z0-9]+$")
IDENTITY_LOCK_PATH = "/run/lock/omnia-openchami-identity.lock"


class IdentityError(RuntimeError):
    """Base error for SMD identity reconciliation."""


class IdentityConflict(IdentityError):
    """Raised when SMD and the PXE mapping describe different identities."""


def normalize_mac(value: str) -> str:
    """Return a lower-case, separator-free MAC address."""
    normalized = re.sub(r"[:-]", "", str(value or "").strip().lower())
    if not MAC_RE.fullmatch(normalized):
        raise IdentityError(f"Invalid MAC address: {value!r}")
    return normalized


def display_mac(value: str) -> str:
    """Return a normalized MAC address using colon separators."""
    normalized = normalize_mac(value)
    return ":".join(normalized[index:index + 2] for index in range(0, 12, 2))


def normalize_service_tag(value: str) -> str:
    """Normalize the physical-server identifier used to build an SMD FRUID."""
    normalized = str(value or "").strip().upper()
    if not SERVICE_TAG_RE.fullmatch(normalized):
        raise IdentityError(
            "SERVICE_TAG must contain only ASCII letters and digits: "
            f"{value!r}"
        )
    return normalized


def normalize_ip(value: str) -> str:
    """Return a canonical IP address."""
    try:
        return str(ipaddress.ip_address(str(value or "").strip()))
    except ValueError as exc:
        raise IdentityError(f"Invalid IP address: {value!r}") from exc


def node_bmc_xname(node_xname: str) -> str:
    """Return the parent NodeBMC XNAME for a Node XNAME."""
    if not XNAME_RE.fullmatch(node_xname):
        raise IdentityError(f"Unsupported Node XNAME: {node_xname!r}")
    return node_xname[:-2]


class SMDIdentityResolver:
    """Use SMD's FRU inventory as the persistent Service Tag registry."""

    def __init__(self, smd_client):
        self.smd = smd_client

    def resolve_nodes(
        self,
        nodes: Iterable[dict[str, Any]],
        check_mode: bool = False,
    ) -> dict[str, Any]:
        """Resolve XNAMEs and bootstrap missing Service Tag FRU records."""
        if check_mode:
            return self._resolve_nodes(nodes, check_mode=True)
        with self._exclusive_lock():
            return self._resolve_nodes(nodes, check_mode=False)

    def _resolve_nodes(
        self,
        nodes: Iterable[dict[str, Any]],
        check_mode: bool,
    ) -> dict[str, Any]:
        original_nodes = [dict(node) for node in nodes]
        self._validate_input(original_nodes)

        interfaces = self.smd.interfaces()
        components = self.smd.components()
        hardware = self.smd.hardware_inventory()

        interface_by_mac = self._interfaces_by_mac(interfaces)
        components_by_id = {
            str(component.get("ID", "")).strip(): component
            for component in components
            if component.get("ID")
        }
        node_xnames = {
            xname
            for xname, component in components_by_id.items()
            if str(component.get("Type", "")).lower() == "node"
        }
        hardware_by_tag, hardware_by_xname = self._hardware_indexes(hardware)
        hardware_xnames = set(hardware_by_xname)
        interface_component_xnames = {
            str(interface.get("ComponentID", "")).strip()
            for interface in interfaces
            if interface.get("ComponentID")
        }
        interface_node_xnames = {
            str(interface.get("ComponentID", "")).strip()
            for interface in interfaces
            if str(interface.get("Type", "")).lower() == "node"
            and interface.get("ComponentID")
        }

        used_node_xnames = (
            set(node_xnames) | hardware_xnames | interface_node_xnames
        )
        used_component_xnames = (
            set(components_by_id) | hardware_xnames | interface_component_xnames
        )
        resolved_by_index = {}
        pending_inventory = []
        claimed_xnames = set()

        # Pre-compute all defensible bootstrap bindings. This prevents a new
        # row from being allocated over an existing, not-yet-migrated node.
        bootstrap_evidence = {}
        for index, node in enumerate(original_nodes):
            tag = normalize_service_tag(node.get("SERVICE_TAG", ""))
            if tag not in hardware_by_tag:
                evidence = self._bootstrap_xname(node, interface_by_mac)
                if evidence:
                    bootstrap_evidence[index] = evidence
        evidenced_xnames = set(bootstrap_evidence.values())
        unclaimed_existing = node_xnames - hardware_xnames - evidenced_xnames

        for index, node in sorted(
            enumerate(original_nodes),
            key=lambda item: normalize_service_tag(
                item[1].get("SERVICE_TAG", "")
            ),
        ):
            tag = normalize_service_tag(node.get("SERVICE_TAG", ""))
            matches = hardware_by_tag.get(tag, [])
            if len(matches) > 1:
                xnames = sorted(
                    str(record.get("ID", "")).strip() for record in matches
                )
                raise IdentityConflict(
                    f"SERVICE_TAG {tag} maps to multiple SMD XNAMEs: "
                    + ", ".join(xnames)
                )

            if matches:
                xname = self._hardware_xname(matches[0], tag)
            else:
                xname = bootstrap_evidence.get(index)
                if not xname:
                    if unclaimed_existing:
                        raise IdentityConflict(
                            f"Cannot allocate an XNAME for new SERVICE_TAG {tag}; "
                            "SMD still has node components without Service Tag "
                            "inventory: " + ", ".join(sorted(unclaimed_existing))
                        )
                    xname = self._allocate_xname(
                        used_node_xnames,
                        used_component_xnames,
                    )
                self._assert_hardware_xname_available(
                    xname,
                    tag,
                    hardware_by_xname,
                )
                pending_inventory.append(self._inventory_record(xname, tag))

            if xname in claimed_xnames:
                raise IdentityConflict(
                    f"Multiple PXE rows resolve to SMD XNAME {xname}"
                )
            claimed_xnames.add(xname)
            used_node_xnames.add(xname)
            used_component_xnames.update((xname, node_bmc_xname(xname)))
            self._assert_network_bindings(node, xname, interface_by_mac)
            resolved_by_index[index] = self._with_xname(node, xname, tag)

        resolved = [resolved_by_index[index] for index in range(len(original_nodes))]
        created = []
        if pending_inventory and not check_mode:
            self.smd.create_hardware_inventory(pending_inventory)
            created = self._verify_inventory(pending_inventory)

        return {
            "changed": bool(pending_inventory),
            "nodes": resolved,
            "identity_source": "smd_hardware_inventory",
            "planned_inventory_xnames": [
                record["ID"] for record in pending_inventory
            ],
            "created_inventory_xnames": created,
        }

    @staticmethod
    @contextlib.contextmanager
    def _exclusive_lock():
        """Serialize SMD identity allocation on the OIM host."""
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(IDENTITY_LOCK_PATH, flags, 0o600)
        except OSError as exc:
            raise IdentityError(
                f"Unable to open identity lock {IDENTITY_LOCK_PATH}: {exc}"
            ) from exc
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise IdentityError(
                    f"Identity lock is not a regular file: {IDENTITY_LOCK_PATH}"
                )
            if metadata.st_uid != os.geteuid():
                raise IdentityError(
                    f"Identity lock has an unexpected owner: {IDENTITY_LOCK_PATH}"
                )
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    @staticmethod
    def _validate_input(nodes: list[dict[str, Any]]):
        if not nodes:
            raise IdentityError("At least one PXE mapping row is required")
        seen = {
            "SERVICE_TAG": set(),
            "ADMIN_MAC": set(),
            "BMC_MAC": set(),
            "ADMIN_IP": set(),
            "BMC_IP": set(),
        }
        for node in nodes:
            values = {
                "SERVICE_TAG": normalize_service_tag(
                    node.get("SERVICE_TAG", "")
                ),
                "ADMIN_MAC": normalize_mac(node.get("ADMIN_MAC", "")),
                "BMC_MAC": normalize_mac(node.get("BMC_MAC", "")),
                "ADMIN_IP": normalize_ip(node.get("ADMIN_IP", "")),
                "BMC_IP": normalize_ip(node.get("BMC_IP", "")),
            }
            for field, value in values.items():
                if value in seen[field]:
                    raise IdentityConflict(f"Duplicate {field} value {value!r}")
                seen[field].add(value)

    @staticmethod
    def _interfaces_by_mac(interfaces) -> dict[str, dict[str, Any]]:
        result = {}
        for interface in interfaces:
            mac = interface.get("MACAddress") or interface.get("ID")
            if not mac:
                continue
            normalized = normalize_mac(mac)
            existing = result.get(normalized)
            component_id = str(interface.get("ComponentID", "")).strip()
            if existing and str(existing.get("ComponentID", "")).strip() != component_id:
                raise IdentityConflict(
                    f"SMD MAC {display_mac(normalized)} maps to multiple components"
                )
            result[normalized] = interface
        return result

    @staticmethod
    def _hardware_indexes(hardware):
        by_tag = {}
        by_xname = {}
        for record in hardware:
            if str(record.get("Type", "")).lower() != "node":
                continue
            xname = str(record.get("ID", "")).strip()
            if not xname:
                continue
            if xname in by_xname:
                raise IdentityConflict(
                    f"SMD Hardware Inventory contains duplicate XNAME {xname}"
                )
            by_xname[xname] = record
            tag_value = (
                record.get("PopulatedFRU", {})
                .get("NodeFRUInfo", {})
                .get("SerialNumber", "")
            )
            if tag_value:
                tag = normalize_service_tag(tag_value)
                by_tag.setdefault(tag, []).append(record)
        return by_tag, by_xname

    @staticmethod
    def _hardware_xname(record, tag):
        xname = str(record.get("ID", "")).strip()
        if not XNAME_RE.fullmatch(xname):
            raise IdentityConflict(
                f"SERVICE_TAG {tag} is attached to unsupported XNAME {xname!r}"
            )
        return xname

    @staticmethod
    def _bootstrap_xname(node, interface_by_mac):
        admin_mac = normalize_mac(node.get("ADMIN_MAC", ""))
        bmc_mac = normalize_mac(node.get("BMC_MAC", ""))
        admin_interface = interface_by_mac.get(admin_mac)
        bmc_interface = interface_by_mac.get(bmc_mac)
        candidates = []

        if admin_interface:
            component_id = str(admin_interface.get("ComponentID", "")).strip()
            if str(admin_interface.get("Type", "")).lower() != "node":
                raise IdentityConflict(
                    f"ADMIN_MAC {display_mac(admin_mac)} is attached to "
                    f"non-Node component {component_id}"
                )
            candidates.append(component_id)

        if bmc_interface:
            component_id = str(bmc_interface.get("ComponentID", "")).strip()
            if str(bmc_interface.get("Type", "")).lower() != "nodebmc":
                raise IdentityConflict(
                    f"BMC_MAC {display_mac(bmc_mac)} is attached to "
                    f"non-NodeBMC component {component_id}"
                )
            candidates.append(component_id + "n0")

        if candidates and len(set(candidates)) != 1:
            raise IdentityConflict(
                f"ADMIN_MAC and BMC_MAC for SERVICE_TAG "
                f"{normalize_service_tag(node.get('SERVICE_TAG', ''))} "
                "resolve to different XNAMEs"
            )
        if not candidates:
            return None
        xname = candidates[0]
        if not XNAME_RE.fullmatch(xname):
            raise IdentityConflict(
                f"SMD bootstrap evidence resolved to unsupported XNAME {xname!r}"
            )
        return xname

    @staticmethod
    def _assert_hardware_xname_available(xname, tag, hardware_by_xname):
        existing = hardware_by_xname.get(xname)
        if not existing:
            return
        existing_tag = (
            existing.get("PopulatedFRU", {})
            .get("NodeFRUInfo", {})
            .get("SerialNumber", "")
        )
        if not existing_tag:
            raise IdentityConflict(
                f"SMD XNAME {xname} already has Hardware Inventory without "
                "a Service Tag"
            )
        if normalize_service_tag(existing_tag) != tag:
            raise IdentityConflict(
                f"SMD XNAME {xname} is already assigned to SERVICE_TAG "
                f"{normalize_service_tag(existing_tag)}"
            )

    @staticmethod
    def _assert_network_bindings(node, xname, interface_by_mac):
        expected = {
            "ADMIN_MAC": (
                normalize_mac(node.get("ADMIN_MAC", "")),
                xname,
            ),
            "BMC_MAC": (
                normalize_mac(node.get("BMC_MAC", "")),
                node_bmc_xname(xname),
            ),
        }
        for field, (mac, expected_component) in expected.items():
            interface = interface_by_mac.get(mac)
            if not interface:
                continue
            actual_component = str(interface.get("ComponentID", "")).strip()
            if actual_component != expected_component:
                raise IdentityConflict(
                    f"{field} {display_mac(mac)} belongs to SMD component "
                    f"{actual_component}, not {expected_component}"
                )

        expected_ips = {
            normalize_ip(node.get("ADMIN_IP", "")): xname,
            normalize_ip(node.get("BMC_IP", "")): node_bmc_xname(xname),
        }
        for interface in interface_by_mac.values():
            component_id = str(interface.get("ComponentID", "")).strip()
            for address in interface.get("IPAddresses", []) or []:
                value = address.get("IPAddress", "") if isinstance(address, dict) else ""
                if not value:
                    continue
                canonical = normalize_ip(value)
                expected_component = expected_ips.get(canonical)
                if expected_component and component_id != expected_component:
                    raise IdentityConflict(
                        f"IP address {canonical} belongs to SMD component "
                        f"{component_id}, not {expected_component}"
                    )

    def _inventory_record(self, xname, tag):
        # The location fields are deliberately XNAME-based rather than
        # hostname-based. Hostname is mutable and is reconciled in Metadata
        # Service; the SMD record exists only to persist physical identity.
        return {
            "ID": xname,
            "NodeLocationInfo": {
                "Id": xname,
                "Name": xname,
                "Description": "Omnia managed node identity",
                "HostName": "",
            },
            "PopulatedFRU": {
                "NodeFRUInfo": {
                    "SerialNumber": tag,
                }
            },
        }

    def _verify_inventory(self, records):
        hardware = self.smd.hardware_inventory()
        by_tag, _ = self._hardware_indexes(hardware)
        verified = []
        for record in records:
            tag = normalize_service_tag(
                record["PopulatedFRU"]["NodeFRUInfo"]["SerialNumber"]
            )
            matches = by_tag.get(tag, [])
            if len(matches) != 1 or matches[0].get("ID") != record["ID"]:
                raise IdentityConflict(
                    f"SMD did not persist a unique SERVICE_TAG {tag} mapping "
                    f"for XNAME {record['ID']}"
                )
            verified.append(record["ID"])
        return verified

    @staticmethod
    def _allocate_xname(
        used_node_xnames: set[str],
        used_component_xnames: set[str],
    ) -> str:
        index = 0
        while True:
            c_index = index // 100
            s_index = (index // 10) % 10
            b_index = index % 10
            candidate = f"x1000c{c_index}s{s_index}b{b_index}n0"
            if (
                candidate not in used_node_xnames
                and node_bmc_xname(candidate) not in used_component_xnames
            ):
                return candidate
            index += 1

    @staticmethod
    def _with_xname(node, xname, tag):
        resolved = dict(node)
        resolved["SERVICE_TAG"] = tag
        resolved["XNAME"] = xname
        return resolved
