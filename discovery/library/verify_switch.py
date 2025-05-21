#  Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

#!/usr/bin/python
"""
Ansible module to verify switch connectivity and BMC static range matching.
"""
import subprocess
import ipaddress
from ansible.module_utils.basic import AnsibleModule

def get_matching_interface_ip(ip_range: str, interface: str, netmask_bits: int):
    """
    Finds the IP on the given NIC that matches the subnet defined by the IP range and netmask.

    Args:
        ip_range (str): IP range like '10.3.0.0-10.3.255.255'
        interface (str): NIC name, e.g., eno8303
        netmask_bits (int): Netmask bits, e.g., 16

    Returns:
        Tuple[str, str, str]: (network_address, matched_ip, netmask) or None if no match
    """
    first_ip = ip_range.split("-")[0]
    network_obj = ipaddress.ip_network(f"{first_ip}/{netmask_bits}", strict=False)

    try:
        result = subprocess.run(
            ["ip", "addr", "show", interface],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get IPs from interface {interface}: {e}")

    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("inet "):
            ip_with_prefix = line.split()[1]
            ip_net = ipaddress.ip_interface(ip_with_prefix)
            if ip_net.ip in network_obj:
                return {
                        "network": str(ip_net.network.network_address),
                        "interface_ip": str(ip_net.ip),
                        "netmask": str(ip_net.netmask)
                    }
    return None

def is_ip_reachable(ip):
    """Checks if an IP is reachable using the ping command."""
    result = subprocess.run(["ping", "-c", '1', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return result.returncode == 0

def verify_switch(switch_ip, bmc_static_range, netmask_bits, oim_nic_name):
    """
    Verifies the switch by checking if it is reachable and if the BMC static range matches the NIC.
    """
    interface_data = get_matching_interface_ip(bmc_static_range, oim_nic_name, netmask_bits)
    ping_status = is_ip_reachable(switch_ip)
    return ping_status, interface_data

def main():
    "Main function to run the verify_switch module."
    module_args = {
        'groups_roles_info':{'type':'dict', 'required':True},
        'netmask_bits':{'type':'str', 'required':True},
        'oim_nic_name':{'type':'str', 'required':True}
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    groups_roles_info = module.params['groups_roles_info']
    netmask_bits = module.params['netmask_bits']
    oim_nic_name = module.params['oim_nic_name']
    verified_switch_groups = {}
    unreachable_switch_groups = {}
    invalid_switch_groups = {}
    switch_status = False
    ping_status = False

    for group, details in groups_roles_info.items():
        if not details.get("switch_status"):
            continue

        switch_info = details.get("switch_details", {})
        switch_ip = switch_info.get("ip")
        bmc_static_range = details.get("bmc_details", {}).get('static_range', '')

        if switch_ip:
            try:
                ping_status, bmc_interface_data = verify_switch(switch_ip,
                                                                bmc_static_range,
                                                                netmask_bits,
                                                                oim_nic_name)
            except Exception as e:
                print(str(e))

            switch_status = switch_status or (ping_status and bmc_interface_data)
            if ping_status:
                if bmc_interface_data:
                    details["bmc_details"].update(bmc_interface_data)
                    verified_switch_groups[group] = details
                else:
                    details['switch_status'] = False
                    invalid_switch_groups[group] = details
            else:
                details['switch_status'] = False
                unreachable_switch_groups[group] = details
        else:
            module.fail_json(msg=f"Missing switch IP for group {group}")

    module.exit_json(
        changed=False,
        verified_switch_groups=verified_switch_groups,
        invalid_switch_groups=invalid_switch_groups,
        unreachable_switch_groups=unreachable_switch_groups,
        switch_status=switch_status,
        groups_roles_info=groups_roles_info,
    )

if __name__ == '__main__':
    main()
