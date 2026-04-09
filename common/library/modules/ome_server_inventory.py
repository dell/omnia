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

"""Ansible module to collect server inventory from Dell OpenManage Enterprise (OME)."""

import json
import urllib3
from ansible.module_utils.basic import AnsibleModule

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOCUMENTATION = r'''
---
module: ome_server_inventory
short_description: Collect server inventory from Dell OME
description:
    - This module connects to Dell OpenManage Enterprise (OME) and collects
      server inventory information including service tags, iDRAC details,
      and network interface information.
options:
    ome_ip:
        description: IP address or hostname of the OME server
        required: true
        type: str
    ome_username:
        description: Username for OME authentication
        required: true
        type: str
    ome_password:
        description: Password for OME authentication
        required: true
        type: str
        no_log: true
    device_type:
        description: Device type to filter (1000 for servers)
        required: false
        type: int
        default: 1000
    verify_ssl:
        description: Whether to verify SSL certificates
        required: false
        type: bool
        default: false
author:
    - Dell Inc.
'''

EXAMPLES = r'''
- name: Collect server inventory from OME
  ome_server_inventory:
    ome_ip: "192.168.1.100"
    ome_username: "admin"
    ome_password: "password"
  register: inventory_result
'''

RETURN = r'''
devices:
    description: List of discovered server devices with inventory details
    type: list
    returned: always
    sample:
        - service_tag: "ABC1234"
          idrac_hostname: "idrac-server01"
          idrac_ip: "192.168.1.10"
          idrac_mac: "AA:BB:CC:DD:EE:01"
          first_nic_name: "NIC.Integrated.1-1-1"
          first_nic_mac: "AA:BB:CC:DD:EE:10"
          group_name: "Rack-A"
          model: "PowerEdge R640"
          ib_nic_name: "NIC.Mezzanine.1-1-1"
          ib_nic_mac: "AA:BB:CC:DD:EE:20"
'''


class OMEClient:
    """Client for interacting with Dell OpenManage Enterprise REST API."""

    def __init__(self, ip, username, password, verify_ssl=False):
        self.base_url = f"https://{ip}"
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.auth_token = None

    def authenticate(self):
        """Authenticate with OME and obtain session token."""
        auth_url = f"{self.base_url}/api/SessionService/Sessions"
        auth_payload = {
            "UserName": self.username,
            "Password": self.password,
            "SessionType": "API"
        }
        headers = {"Content-Type": "application/json"}

        response = self.session.post(auth_url, json=auth_payload, headers=headers)
        if response.status_code in [200, 201]:
            self.auth_token = response.headers.get("X-Auth-Token")
            self.session.headers.update({"X-Auth-Token": self.auth_token})
            return True
        return False

    def logout(self):
        """Logout and invalidate the session."""
        if self.auth_token:
            try:
                logout_url = f"{self.base_url}/api/SessionService/Sessions('current')"
                self.session.delete(logout_url)
            except Exception:
                pass

    def get_paginated(self, url):
        """Handle paginated API responses."""
        results = []
        while url:
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                results.extend(data.get("value", []))
                next_link = data.get("@odata.nextLink")
                url = f"{self.base_url}{next_link}" if next_link and not next_link.startswith("http") else next_link
            else:
                break
        return results

    def get_all_devices(self, device_type=None):
        """Get all devices managed by OME, optionally filtered by type."""
        url = f"{self.base_url}/api/DeviceService/Devices"
        devices = self.get_paginated(url)
        if device_type:
            devices = [d for d in devices if d.get("Type") == device_type]
        return devices

    def get_device_inventory(self, device_id, inventory_type):
        """Get specific inventory type for a device."""
        url = f"{self.base_url}/api/DeviceService/Devices({device_id})/InventoryDetails('{inventory_type}')"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json()
        return {}

    def get_device_management_info(self, device_id):
        """Get device management info including iDRAC details."""
        url = f"{self.base_url}/api/DeviceService/Devices({device_id})/DeviceManagement"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json().get("value", [])
        return []

    def build_device_group_map(self):
        """Build a device_id -> group_name map from Custom Groups -> Static Groups in OME.

        Primary strategy: locate the 'Static Groups' container by name, then select
        all groups whose ParentId matches that container's Id.
        Fallback: skip well-known OME system/container group names and use any group
        that has at least one device.
        """
        device_group_map = {}

        all_groups_url = f"{self.base_url}/api/GroupService/Groups"
        all_groups = self.get_paginated(all_groups_url)

        # Names of OME built-in container/system groups to always skip
        _SYSTEM_NAMES = {
            "All Devices", "Ungrouped Devices", "Recently Discovered",
            "System Groups", "Custom Groups", "Static Groups",
            "Query Groups", "Servers", "Chassis", "IO Modules",
            "Dell iDRAC Servers", "Non-Dell Servers", "Plugins",
        }

        # Primary: find the "Static Groups" container and use ParentId
        static_container = next(
            (g for g in all_groups if g.get("Name") == "Static Groups"), None
        )

        if static_container:
            container_id = static_container.get("Id")
            target_groups = [
                g for g in all_groups if g.get("ParentId") == container_id
            ]
        else:
            # Fallback: any group not in the system names list
            target_groups = [
                g for g in all_groups
                if g.get("Name", "") not in _SYSTEM_NAMES
            ]

        for group in target_groups:
            group_id = group.get("Id")
            group_name = group.get("Name", "")
            if not group_id or not group_name:
                continue

            # Use the navigation link from the group object (Dell official approach)
            nav_link = group.get("Devices@odata.navigationLink", "")
            if nav_link:
                devices_url = f"{self.base_url}{nav_link}" if nav_link.startswith("/") else nav_link
            else:
                devices_url = f"{self.base_url}/api/GroupService/Groups({group_id})/Devices"

            group_devices = self.get_paginated(devices_url)
            for gd in group_devices:
                dev_id = gd.get("Id")
                if dev_id and dev_id not in device_group_map:
                    device_group_map[dev_id] = group_name

        empty_groups = [g.get("Name") for g in target_groups
                         if g.get("Name") not in [device_group_map.get(d) for d in device_group_map]]

        debug = {
            "all_group_names": [g.get("Name") for g in all_groups],
            "static_container_found": static_container is not None,
            "static_container_id": static_container.get("Id") if static_container else None,
            "target_group_names": [g.get("Name") for g in target_groups],
            "device_ids_mapped": list(device_group_map.keys()),
            "empty_groups": empty_groups,
        }
        return device_group_map, debug


def extract_server_info(client, device, device_group_map=None):
    """Extract required fields from device and its inventory."""
    device_id = device.get("Id")

    info = {
        "service_tag": device.get("Identifier") or device.get("DeviceServiceTag", ""),
        "idrac_hostname": "",
        "model": device.get("Model", ""),
        "idrac_ip": "",
        "idrac_mac": "",
        "first_nic_name": "",
        "first_nic_mac": "",
        "group_name": "",
        "ib_nic_name": "",
        "ib_nic_mac": ""
    }

    # Get management IP from device info
    mgmt_list = device.get("DeviceManagement", [])
    if mgmt_list:
        for mgmt in mgmt_list:
            if mgmt.get("ManagementType") == 2:  # iDRAC management
                info["idrac_ip"] = mgmt.get("NetworkAddress", "")
                info["idrac_mac"] = mgmt.get("MacAddress", "")
                info["idrac_hostname"] = (
                    mgmt.get("InstrumentationName") or
                    mgmt.get("DnsName") or
                    ""
                )
                break

    # If not found in device info, try DeviceManagement endpoint
    if not info["idrac_ip"]:
        mgmt_info = client.get_device_management_info(device_id)
        for mgmt in mgmt_info:
            if mgmt.get("ManagementType") == 2:
                info["idrac_ip"] = mgmt.get("NetworkAddress", "")
                info["idrac_mac"] = mgmt.get("MacAddress", "")
                info["idrac_hostname"] = (
                    mgmt.get("InstrumentationName") or
                    mgmt.get("DnsName") or
                    ""
                )
                break

    # Get network interface inventory for first NIC
    nic_inventory = client.get_device_inventory(device_id, "serverNetworkInterfaces")
    nic_info_list = nic_inventory.get("InventoryInfo", [])

    # Find first non-iDRAC NIC
    for nic in nic_info_list:
        nic_id = nic.get("NicId", "")
        if "iDRAC" not in nic_id.upper():
            ports = nic.get("Ports", [])
            if ports:
                first_port = ports[0]
                partitions = first_port.get("Partitions", [])
                if partitions:
                    info["first_nic_name"] = nic_id
                    info["first_nic_mac"] = partitions[0].get("CurrentMacAddress", "")
                    break

    # Fallback to deviceNics inventory type
    if not info["first_nic_mac"]:
        device_nics = client.get_device_inventory(device_id, "deviceNics")
        for nic in device_nics.get("InventoryInfo", []):
            nic_id = nic.get("NicId", "")
            if "iDRAC" not in str(nic_id).upper():
                info["first_nic_name"] = nic_id
                info["first_nic_mac"] = nic.get("MacAddress", "")
                break

    # Get InfiniBand NIC: first NIC whose ID or VendorName indicates IB
    _IB_KEYWORDS = ("infiniband", "mellanox", "connectx", "hdr", "edr", "fdr", "qdr", " ib ")
    for nic in nic_info_list:
        nic_id = nic.get("NicId", "")
        vendor = nic.get("VendorName", "") or ""
        nic_label = (nic_id + " " + vendor).lower()
        if any(kw in nic_label for kw in _IB_KEYWORDS):
            ports = nic.get("Ports", [])
            if ports:
                partitions = ports[0].get("Partitions", [])
                if partitions:
                    info["ib_nic_name"] = nic_id
                    info["ib_nic_mac"] = partitions[0].get("CurrentMacAddress", "")
                    break

    # Get group name from pre-built device→group map
    if device_group_map:
        info["group_name"] = device_group_map.get(device_id, "")

    return info


def main():
    """Main function for the Ansible module."""
    module_args = {
        "ome_ip": {"type": "str", "required": True},
        "ome_username": {"type": "str", "required": True},
        "ome_password": {"type": "str", "required": True, "no_log": True},
        "device_type": {"type": "int", "required": False, "default": 1000},
        "verify_ssl": {"type": "bool", "required": False, "default": False}
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if not HAS_REQUESTS:
        module.fail_json(msg="The 'requests' Python library is required for this module")

    ome_ip = module.params['ome_ip']
    ome_username = module.params['ome_username']
    ome_password = module.params['ome_password']
    device_type = module.params['device_type']
    verify_ssl = module.params['verify_ssl']

    client = OMEClient(ome_ip, ome_username, ome_password, verify_ssl)

    try:
        if not client.authenticate():
            module.fail_json(msg=f"Failed to authenticate with OME at {ome_ip}")

        devices = client.get_all_devices(device_type)
        device_group_map, group_debug = client.build_device_group_map()

        if not group_debug["static_container_found"]:
            module.warn("OME: 'Static Groups' container not found under Custom Groups. "
                        "Group names will not be assigned to any device.")
        elif not group_debug["target_group_names"]:
            module.warn("OME: 'Static Groups' container found but contains no groups. "
                        "Group names will not be assigned to any device.")
        elif group_debug["empty_groups"]:
            for grp in group_debug["empty_groups"]:
                module.warn(f"OME: Static group '{grp}' exists but has no devices assigned. "
                            f"Devices in this group will fall back to the default functional group.")

        server_info_list = []
        for device in devices:
            info = extract_server_info(client, device, device_group_map)
            if info["service_tag"]:  # Only include devices with valid service tags
                server_info_list.append(info)

        module.exit_json(
            changed=False,
            devices=server_info_list,
            device_count=len(server_info_list),
            group_debug=group_debug
        )

    except Exception as e:
        module.fail_json(msg=f"Error collecting OME inventory: {str(e)}")
    finally:
        client.logout()


if __name__ == '__main__':
    main()
