#!/usr/bin/python
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

"""Ansible module to collect server inventory from iDRACs via Redfish."""

import concurrent.futures
import logging
import re
import time
import urllib3
from ansible.module_utils.basic import AnsibleModule

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger("magellan_inventory")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOCUMENTATION = r'''
---
module: magellan_inventory
short_description: Collect server inventory from iDRACs via Redfish
description:
    - Connects to each BMC in the admin inventory CSV and collects
      service tag, MAC addresses, InfiniBand NIC details, and location info
      using the iDRAC Redfish API.
options:
    admin_inventory:
        description: List of dicts parsed from the admin inventory CSV
        required: true
        type: list
    bmc_username:
        description: Username for iDRAC authentication
        required: true
        type: str
    bmc_password:
        description: Password for iDRAC authentication
        required: true
        type: str
        no_log: true
    default_functional_group:
        description: Default functional group when not provided in admin inventory
        required: false
        type: str
        default: "slurm_node_aarch64"
    default_group_name:
        description: Default group name when not provided in admin inventory
        required: false
        type: str
        default: "grp0"
    ib_subnet:
        description: InfiniBand subnet; when empty IB detection is skipped
        required: false
        type: str
        default: ""
    verify_ssl:
        description: Whether to verify SSL certificates
        required: false
        type: bool
        default: false
    timeout:
        description: HTTP request timeout in seconds
        required: false
        type: int
        default: 30
    max_retries:
        description: Maximum retries per Redfish request
        required: false
        type: int
        default: 3
author:
    - Dell Inc.
'''

EXAMPLES = r'''
- name: Collect iDRAC inventory via Redfish
  magellan_inventory:
    admin_inventory: "{{ admin_inventory_data }}"
    bmc_username: "{{ bmc_username }}"
    bmc_password: "{{ bmc_password }}"
    default_functional_group: "slurm_node_aarch64"
    default_group_name: "grp0"
    ib_subnet: "192.168.2.0"
  register: magellan_inventory_result
'''

RETURN = r'''
servers:
    description: List of discovered server inventory dicts
    type: list
    returned: always
'''

MAC_RE = re.compile(r"[0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}")

IB_NIC_RE = re.compile(
    r"^(InfiniBand\.PCIe\.Slot\.|InfiniBand\.Slot\.|NIC\.InfiniBand\.)([0-9a-fA-F]+)-([0-9]+)$"
)
IB_SINGLE_RE = re.compile(r"^InfiniBand\.Single-[0-9]+$")


def normalize_mac(mac):
    """Return a MAC address normalized to uppercase with colon separators."""
    if not mac:
        return ""
    mac = str(mac).strip().upper()
    mac = mac.replace("-", ":")
    if len(mac) == 12:
        return ":".join(mac[i:i + 2] for i in range(0, 12, 2))
    return mac


def _get_value(server, *keys):
    """Return the first matching value from a server dict, case-insensitive."""
    for key in keys:
        if key in server:
            return server[key]
        if key.lower() in server:
            return server[key.lower()]
        if key.upper() in server:
            return server[key.upper()]
    return None


def redfish_get(session, base_url, path, auth, verify_ssl, timeout, max_retries):
    """Perform a Redfish GET with retries."""
    url = f"{base_url}{path}"
    for attempt in range(1, max_retries + 1):
        last_exc = None
        try:
            response = session.get(url, auth=auth, verify=verify_ssl, timeout=timeout)
            if response.status_code < 500:
                return response
            logger.warning("Redfish GET %s returned HTTP %s (attempt %d/%d)",
                           url, response.status_code, attempt, max_retries)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            logger.warning("Redfish GET %s failed (attempt %d/%d): %s",
                           url, attempt, max_retries, type(exc).__name__)
            last_exc = exc
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    if last_exc:
        raise last_exc
    return response


def format_ib_nic_name(function_id, port_id=""):
    """Convert an iDRAC network function Id to a cloud-init compatible IB_NIC_NAME."""
    name = function_id or port_id or ""
    if not name:
        return ""

    # Already acceptable cloud-init formats
    if IB_NIC_RE.match(name) or IB_SINGLE_RE.match(name):
        return name

    # e.g. NIC.Slot.7-1 -> InfiniBand.Slot.7-1
    m = re.match(r"^NIC\.(.+?)-([0-9]+)$", name, re.IGNORECASE)
    if m:
        middle = m.group(1)
        port = m.group(2)
        if "slot" in middle.lower() or "pcie" in middle.lower():
            # Normalize "PCIe.Slot.7" or "Slot.7" -> "Slot.7"
            middle = re.sub(r"^(PCIe\.?)?(Slot\.?)?", "", middle, flags=re.IGNORECASE)
            middle = middle.strip(".")
            if middle:
                return f"InfiniBand.Slot.{middle}-{port}"
        return f"InfiniBand.Single-{port}"

    # e.g. InfiniBand.Embedded.1-1 -> InfiniBand.Single-1
    m = re.match(r"^InfiniBand\.(.+?)-([0-9]+)$", name, re.IGNORECASE)
    if m:
        return f"InfiniBand.Single-{m.group(2)}"

    # e.g. InfiniBand.Slot.7 or InfiniBand.PCIe.Slot.7 (no port suffix) -> InfiniBand.Slot.7-1
    m = re.match(r"^InfiniBand\.(?:(?:PCIe)\.?)?Slot\.([0-9a-fA-F]+)$", name, re.IGNORECASE)
    if m:
        return f"InfiniBand.Slot.{m.group(1)}-1"

    # Bare adapter/function name with no port: append -1
    if name:
        return f"InfiniBand.Single-1"

    return ""


def is_infiniBand_function(func_data, adapter_data):
    """Determine whether a network device function is InfiniBand."""
    func_type = (func_data.get("NetDevFuncType") or "").lower()
    # NetDevFuncType is the authoritative source when present.
    if func_type == "infiniband":
        return True
    if func_type == "ethernet":
        return False

    # No explicit function type: fall back to identifier / adapter heuristics.
    func_id = func_data.get("Id", "")
    if "infiniband" in func_id.lower():
        return True
    adapter_name = (adapter_data.get("Name") or adapter_data.get("Id") or "").lower()
    adapter_model = (adapter_data.get("Model") or "").lower()
    adapter_manufacturer = (adapter_data.get("Manufacturer") or "").lower()
    if "infiniband" in adapter_name or "mellanox" in adapter_model or "mellanox" in adapter_manufacturer:
        return True
    return False


def collect_server_inventory(admin_server, bmc_username, bmc_password, ib_subnet,
                             verify_ssl, timeout, max_retries, service_tag_field="",
                             system_endpoint="", manager_attributes_endpoint="",
                             manager_endpoint="", managers_collection_endpoint="/redfish/v1/Managers",
                             manager_ethernet_interfaces_endpoint="",
                             systems_collection_endpoint="/redfish/v1/Systems",
                             system_network_adapters_endpoint="",
                             system_ethernet_interfaces_endpoint=""):
    """Collect inventory for a single server from its BMC."""
    bmc_ip = _get_value(admin_server, "BMC_IP")
    if not bmc_ip:
        raise ValueError("Admin inventory entry is missing BMC_IP")

    auth = (bmc_username, bmc_password)
    base_url = f"https://{bmc_ip}"
    session = requests.Session()

    info = {
        "service_tag": "",
        "idrac_hostname": "",
        "model": "",
        "idrac_ip": bmc_ip,
        "idrac_mac": "",
        "idrac_link_status": "",
        "first_nic_name": "",
        "first_nic_mac": "",
        "first_nic_link_status": "",
        "group_name": _get_value(admin_server, "GROUP_NAME") or "grp0",
        "functional_group": _get_value(admin_server, "FUNCTIONAL_GROUP_NAME") or "slurm_node_aarch64",
        "ib_nic_name": "",
        "ib_nic_link_status": "",
        "row": _get_value(admin_server, "ROW") or "",
        "rack": _get_value(admin_server, "RACK") or "",
        "uslot": _get_value(admin_server, "USLOT", "SLOT") or "",
    }

    # Resolve the system endpoint. If a system_endpoint is configured, use it
    # directly; otherwise walk the configured Systems collection and pick the
    # first member.
    if system_endpoint:
        system_path = system_endpoint
        system_resp = redfish_get(session, base_url, system_path,
                                  auth, verify_ssl, timeout, max_retries)
        if system_resp.status_code != 200:
            raise ValueError(f"Failed to fetch system endpoint {system_path}: HTTP {system_resp.status_code}")
        system_data = system_resp.json()
    else:
        systems_resp = redfish_get(session, base_url, systems_collection_endpoint,
                                   auth, verify_ssl, timeout, max_retries)
        if systems_resp.status_code != 200:
            raise ValueError(f"Failed to fetch Systems collection {systems_collection_endpoint}: HTTP {systems_resp.status_code}")
        members = systems_resp.json().get("Members", [])
        system_path = ""
        for member in members:
            path = member.get("@odata.id", "")
            if path:
                system_path = path
                break
        if not system_path:
            raise ValueError("No Systems member found in Redfish response")

        system_data = redfish_get(session, base_url, system_path,
                                  auth, verify_ssl, timeout, max_retries).json()

    csv_service_tag = _get_value(admin_server, "SERVICE_TAG") or ""
    if service_tag_field:
        redfish_service_tag = system_data.get(service_tag_field, "") or ""
    else:
        redfish_service_tag = system_data.get("SKU") or system_data.get("SerialNumber") or ""
    if csv_service_tag and redfish_service_tag:
        if csv_service_tag.upper() != redfish_service_tag.upper():
            raise ValueError(
                f"Service tag mismatch for {bmc_ip}: "
                f"inventory says {csv_service_tag}, BMC reports {redfish_service_tag}"
            )
    info["service_tag"] = csv_service_tag or redfish_service_tag
    info["model"] = system_data.get("Model") or ""

    # Resolve the manager endpoint. Prefer an explicitly configured
    # manager_endpoint, then derive the root from manager_attributes_endpoint,
    # then discover via the Managers collection.
    manager_path = manager_endpoint
    if not manager_path and manager_attributes_endpoint:
        manager_path = manager_attributes_endpoint.rstrip("/")
        if manager_path.endswith("/Attributes"):
            manager_path = manager_path[: -len("/Attributes")]

    if not manager_path:
        managers_resp = redfish_get(session, base_url, managers_collection_endpoint,
                                    auth, verify_ssl, timeout, max_retries)
        if managers_resp.status_code == 200:
            managers = managers_resp.json().get("Members", [])
            for member in managers:
                path = member.get("@odata.id", "")
                if path and ("iDRAC" in path or not manager_path):
                    manager_path = path

    if manager_path:
        eth_coll_path = manager_ethernet_interfaces_endpoint or f"{manager_path}/EthernetInterfaces"
        eth_resp = redfish_get(session, base_url, eth_coll_path,
                               auth, verify_ssl, timeout, max_retries)
        if eth_resp.status_code == 200:
            for eth_member in eth_resp.json().get("Members", []):
                eth_path = eth_member.get("@odata.id", "")
                if not eth_path:
                    continue
                eth_data = redfish_get(session, base_url, eth_path,
                                       auth, verify_ssl, timeout, max_retries).json()
                mac = eth_data.get("MACAddress") or eth_data.get("PermanentMACAddress")
                if mac:
                    info["idrac_mac"] = normalize_mac(mac)
                    info["idrac_link_status"] = eth_data.get("LinkStatus", "Unknown")
                    break

    # Network adapters on the host system
    adapters_path = system_network_adapters_endpoint or f"{system_path}/NetworkAdapters"
    adapters_resp = redfish_get(session, base_url, adapters_path,
                                auth, verify_ssl, timeout, max_retries)
    if adapters_resp.status_code == 200:
        adapters = adapters_resp.json().get("Members", [])
        fallback_eth = {}
        fallback_ib = {}

        first_nic_found = False
        ib_found = False

        for adapter_member in adapters:
            if first_nic_found and ib_found:
                break
            adapter_path = adapter_member.get("@odata.id", "")
            if not adapter_path:
                continue
            try:
                adapter_data = redfish_get(session, base_url, adapter_path,
                                           auth, verify_ssl, timeout, max_retries).json()
            except Exception:
                continue

            funcs_path = adapter_data.get("NetworkDeviceFunctions", {}).get("@odata.id")
            if not funcs_path:
                continue
            funcs_resp = redfish_get(session, base_url, funcs_path,
                                     auth, verify_ssl, timeout, max_retries)
            if funcs_resp.status_code != 200:
                continue

            for func_member in funcs_resp.json().get("Members", []):
                if first_nic_found and ib_found:
                    break
                func_path = func_member.get("@odata.id", "")
                if not func_path:
                    continue
                try:
                    func_data = redfish_get(session, base_url, func_path,
                                            auth, verify_ssl, timeout, max_retries).json()
                except Exception:
                    continue

                func_id = func_data.get("Id", "")
                func_type = (func_data.get("NetDevFuncType") or "").lower()
                eth_data = func_data.get("Ethernet", {}) or {}
                mac = eth_data.get("MACAddress") or eth_data.get("PermanentMACAddress") or ""
                link_status = eth_data.get("LinkStatus") or func_data.get("Status", {}).get("Health") or "Unknown"

                if is_infiniBand_function(func_data, adapter_data):
                    if ib_found:
                        continue
                    ib_name = format_ib_nic_name(func_id)
                    if not fallback_ib or link_status.upper() == "UP":
                        fallback_ib = {
                            "ib_nic_name": ib_name,
                            "ib_nic_link_status": link_status,
                        }
                    if link_status.upper() == "UP":
                        ib_found = True

                elif func_type == "ethernet" or not func_type:
                    if first_nic_found:
                        continue
                    if mac and not fallback_eth:
                        fallback_eth = {
                            "first_nic_name": func_id,
                            "first_nic_mac": normalize_mac(mac),
                            "first_nic_link_status": link_status,
                        }
                    if link_status.upper() == "UP" and mac:
                        info["first_nic_name"] = func_id
                        info["first_nic_mac"] = normalize_mac(mac)
                        info["first_nic_link_status"] = link_status
                        first_nic_found = True

        if not info["first_nic_mac"] and fallback_eth:
            info["first_nic_name"] = fallback_eth["first_nic_name"]
            info["first_nic_mac"] = fallback_eth["first_nic_mac"]
            info["first_nic_link_status"] = fallback_eth["first_nic_link_status"]

        if fallback_ib and ib_subnet:
            info["ib_nic_name"] = fallback_ib["ib_nic_name"]
            info["ib_nic_link_status"] = fallback_ib["ib_nic_link_status"]

    # Fallback: try system EthernetInterfaces if NetworkAdapters yielded nothing
    if not info["first_nic_mac"]:
        eth_if_path = system_ethernet_interfaces_endpoint or f"{system_path}/EthernetInterfaces"
        eth_if_resp = redfish_get(session, base_url, eth_if_path,
                                  auth, verify_ssl, timeout, max_retries)
        if eth_if_resp.status_code == 200:
            for eth_member in eth_if_resp.json().get("Members", []):
                eth_path = eth_member.get("@odata.id", "")
                if not eth_path:
                    continue
                eth_data = redfish_get(session, base_url, eth_path,
                                       auth, verify_ssl, timeout, max_retries).json()
                mac = eth_data.get("MACAddress") or eth_data.get("PermanentMACAddress")
                if mac:
                    info["first_nic_name"] = eth_data.get("Id", "")
                    info["first_nic_mac"] = normalize_mac(mac)
                    info["first_nic_link_status"] = eth_data.get("LinkStatus", "Unknown")
                    break

    # Location data (row, rack, uslot) is intentionally not fetched from the BMC.
    # It must be supplied in the admin inventory; xnames mapping generation is
    # skipped downstream when location data is missing for any server.

    session.close()
    return info


def main():
    module_args = {
        "admin_inventory": {"type": "list", "required": True},
        "bmc_username": {"type": "str", "required": True},
        "bmc_password": {"type": "str", "required": True, "no_log": True},
        "default_functional_group": {"type": "str", "required": False, "default": "slurm_node_aarch64"},
        "default_group_name": {"type": "str", "required": False, "default": "grp0"},
        "ib_subnet": {"type": "str", "required": False, "default": ""},
        "verify_ssl": {"type": "bool", "required": False, "default": False},
        "timeout": {"type": "int", "required": False, "default": 30},
        "max_retries": {"type": "int", "required": False, "default": 3},
        "service_tag_field": {"type": "str", "required": False, "default": ""},
        "system_endpoint": {"type": "str", "required": False, "default": ""},
        "systems_collection_endpoint": {"type": "str", "required": False, "default": "/redfish/v1/Systems"},
        "system_network_adapters_endpoint": {"type": "str", "required": False, "default": ""},
        "system_ethernet_interfaces_endpoint": {"type": "str", "required": False, "default": ""},
        "manager_attributes_endpoint": {"type": "str", "required": False, "default": ""},
        "manager_endpoint": {"type": "str", "required": False, "default": ""},
        "managers_collection_endpoint": {"type": "str", "required": False, "default": "/redfish/v1/Managers"},
        "manager_ethernet_interfaces_endpoint": {"type": "str", "required": False, "default": ""},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    if not HAS_REQUESTS:
        module.fail_json(msg="The 'requests' Python library is required for this module")

    admin_inventory = module.params["admin_inventory"]
    bmc_username = module.params["bmc_username"]
    bmc_password = module.params["bmc_password"]
    default_functional_group = module.params["default_functional_group"]
    default_group_name = module.params["default_group_name"]
    ib_subnet = module.params["ib_subnet"]
    verify_ssl = module.params["verify_ssl"]
    timeout = module.params["timeout"]
    max_retries = module.params["max_retries"]
    service_tag_field = module.params["service_tag_field"]
    system_endpoint = module.params["system_endpoint"]
    systems_collection_endpoint = module.params["systems_collection_endpoint"]
    system_network_adapters_endpoint = module.params["system_network_adapters_endpoint"]
    system_ethernet_interfaces_endpoint = module.params["system_ethernet_interfaces_endpoint"]
    manager_attributes_endpoint = module.params["manager_attributes_endpoint"]
    manager_endpoint = module.params["manager_endpoint"]
    managers_collection_endpoint = module.params["managers_collection_endpoint"]
    manager_ethernet_interfaces_endpoint = module.params["manager_ethernet_interfaces_endpoint"]

    if module.check_mode:
        module.exit_json(changed=False, servers=[])

    servers = []
    failed_servers = []

    def process(entry):
        return collect_server_inventory(
            entry, bmc_username, bmc_password, ib_subnet,
            verify_ssl, timeout, max_retries, service_tag_field,
            system_endpoint, manager_attributes_endpoint,
            manager_endpoint, managers_collection_endpoint,
            manager_ethernet_interfaces_endpoint,
            systems_collection_endpoint,
            system_network_adapters_endpoint,
            system_ethernet_interfaces_endpoint
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_entry = {executor.submit(process, entry): entry for entry in admin_inventory}
        for future in concurrent.futures.as_completed(future_to_entry):
            entry = future_to_entry[future]
            bmc_ip = _get_value(entry, "BMC_IP") or "unknown"
            try:
                server_info = future.result()
                servers.append(server_info)
            except Exception as exc:  # pylint: disable=broad-except
                failed_servers.append({"bmc_ip": bmc_ip, "error": str(exc)})

    servers.sort(key=lambda s: s.get("idrac_ip", ""))

    if not servers:
        module.fail_json(
            msg="No servers could be discovered from the admin inventory. "
                f"Failures: {failed_servers}"
        )

    result = {
        "changed": True,
        "servers": servers,
        "server_count": len(servers),
    }
    if failed_servers:
        result["failed_servers"] = failed_servers
        module.warn(f"Some iDRACs could not be reached: {failed_servers}")

    module.exit_json(**result)


if __name__ == "__main__":
    main()
