# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import omniadb_connection
from ansible.module_utils.omniadb_connection import execute_select_query
from ipaddress import IPv4Address
import sys, re

def check_switch_table():
    """Checks if the cluster.switchinfo table has any entries."""
    query = "SELECT MAX(id) FROM cluster.switchinfo"
    result = execute_select_query(query=query)
    return bool(result and result[0]["max"])

def check_presence_switch_port(switch_name, switch_port):
    """Checks if a switch port is already in the cluster.nodeinfo table."""
    query = """
        SELECT EXISTS(
            SELECT 1 FROM cluster.nodeinfo
            WHERE switch_port = %s AND switch_name = %s
        )
    """
    result = execute_select_query(query=query, params=(switch_port, switch_name))
    return bool(result[0]["exists"]) if result else False

def get_next_node_name(group):
    """Fetch the next available node name based on the last valid node pattern."""
    query = """
        SELECT node
        FROM cluster.nodeinfo
        WHERE group_name = %s
        ORDER BY node DESC;
    """
    result = execute_select_query(query=query, params=(group,))

    # Regular expression pattern: e.g., "grp0node001"
    pattern = re.compile(rf"^{re.escape(group)}node(\d{{3}})$")

    for row in result:
        node_name = row['node']
        match = pattern.match(node_name)
        if match:
            last_number = int(match.group(1))
            next_node_name = f"{group}node{last_number + 1:03d}"
            return next_node_name

    # No matching node found; return the first node name
    return f"{group}node001"

def assign_bmc_admin_ip(cursor, admin_details, admin_subnet, bmc_details,
                        admin_uncorrelated_node_start_ip, discovery_mechanism, mtms_db_path):
    """
    Assigns BMC and admin IP addresses based on the given parameters.

    Args:
        cursor (cursor): A database cursor.
        admin_details (dict): A dictionary containing admin details.
        admin_subnet (str): The admin subnet.
        bmc_details (dict): A dictionary containing BMC details.
        admin_uncorrelated_node_start_ip (str): The starting IP address for uncorrelated admin nodes.
        discovery_mechanism (str): The discovery mechanism.
        mtms_db_path (str): The path to the MTMS database.

    Returns:
        tuple: A tuple containing the BMC IP address and the admin IP address.
    """

    sys.path.insert(0, mtms_db_path)
    import correlation_admin_bmc
    import modify_network_details


    admin_static_start_ip, admin_static_end_ip = list(map(IPv4Address, admin_details.get('static_range').split('-')))
    bmc_static_start_ip, bmc_static_end_ip = list(map(IPv4Address, bmc_details.get('static_range').split('-')))
    admin_netmask_bits = admin_details.get('netmask_bits')
    correlation_status = admin_details.get('correlation_to_admin')


    bmc_ip = modify_network_details.reassign_bmc_ip(cursor, bmc_static_start_ip, bmc_static_end_ip)
    if correlation_status:
        admin_ip = correlation_admin_bmc.correlation_bmc_to_admin(str(bmc_ip), admin_subnet, admin_netmask_bits)
        if admin_static_start_ip <= admin_ip <= admin_static_end_ip:
            output = modify_network_details.check_presence_admin_ip(cursor, admin_ip)
            if output:
                admin_ip = modify_network_details.cal_uncorrelated_admin_ip(cursor, admin_uncorrelated_node_start_ip, admin_static_start_ip,admin_static_end_ip,discovery_mechanism)
        else:
            admin_ip = modify_network_details.cal_uncorrelated_admin_ip(cursor, admin_uncorrelated_node_start_ip, admin_static_start_ip,admin_static_end_ip,discovery_mechanism)
    # Set admin_ip when correlation_status is false
    else:
        admin_ip = modify_network_details.cal_uncorrelated_admin_ip(cursor, admin_uncorrelated_node_start_ip, admin_static_start_ip,admin_static_end_ip,discovery_mechanism)
    return bmc_ip, admin_ip

def main():
    """Main function to execute Ansible module."""
    module_args = dict(
        admin_details=dict(type="dict", required=True),
        admin_subnet=dict(type="str", required=True),
        domain_name=dict(type="str", required=True),
        group_details=dict(type="dict", required=True),
        mtms_db_path=dict(type="str", required=True)
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    # Fetch parameters
    group_details = module.params["group_details"]
    admin_details = module.params["admin_details"]
    mtms_db_path = module.params["mtms_db_path"]
    admin_subnet = module.params["admin_subnet"]
    domain_name = module.params["domain_name"]
    msg = []
    for group_name, group_data in group_details.items():
        if not group_data.get("switch_status"):
            continue
        # Extract switch and bmc details from group_data
        switch_ip = IPv4Address(group_data.get("switch_details", {}).get("ip", ""))
        switch_ports = group_data.get("switch_details", {}).get("ports", "")
        bmc_details = group_data.get("bmc_details", {})
        roles = ','.join(group_data.get("roles", []))
        parent = group_data.get("parent", "")
        location_id = group_data.get("location_id", "")
        architecture = group_data.get("architecture", "")

        # Extract admin network data from admin_details
        admin_uncorrelated_node_start_ip = admin_details.get("admin_uncorrelated_node_start_ip", "")
        if not admin_uncorrelated_node_start_ip:
            admin_uncorrelated_node_start_ip = admin_details.get("static_range", "").split('-')[0]
        admin_uncorrelated_node_start_ip = IPv4Address(admin_uncorrelated_node_start_ip)
        discovery_mechanism = "switch_based"
        bmc_mode = "static"

        # Check if switchinfo table has entries
        if not check_switch_table():
            module.fail_json(msg="Switch table does not contain any input")

        # Fetch switch name from cluster.switchinfo
        query = "SELECT switch_name FROM cluster.switchinfo WHERE switch_ip = %s"
        result = execute_select_query(query=query, params=(str(switch_ip),))
        if not result:
            module.fail_json(msg=f"No switch found with IP {switch_ip}")
        switch_name = result[0]["switch_name"]

        # Process switch ports
        existing_ports = []
        new_added_ports = []

        # Creating cursor
        conn = omniadb_connection.create_connection()
        cursor = conn.cursor()

        for ports in switch_ports.split(','):
            # Fetch node name
            node_name = get_next_node_name(group_name)
            fqdn_hostname = f"{node_name}.{domain_name}"
            expanded_ports = range(int(ports.split("-")[0]), int(ports.split("-")[1]) + 1) if "-" in ports else [int(ports)]
            for port in expanded_ports:
                if not check_presence_switch_port(switch_name, str(port)):
                    bmc_ip, admin_ip = assign_bmc_admin_ip(cursor, admin_details, admin_subnet, bmc_details,
                                                            admin_uncorrelated_node_start_ip, discovery_mechanism, mtms_db_path)
                    omniadb_connection.insert_node_info(
                    None, node_name, fqdn_hostname, None, admin_ip, bmc_ip,
                    group_name, roles, parent, location_id, architecture, discovery_mechanism, bmc_mode, switch_ip, switch_name, port
                )
                    new_added_ports.append(str(port))
                else:
                    existing_ports.append(str(port))
        msg_log = f"For Group - {group_name} Switch details - ip:{switch_ip} "
        if new_added_ports:
            msg_log+=f"New added ports:{','.join(new_added_ports)} "
        if existing_ports:
            msg_log+=f"Existing ports - {','.join(existing_ports)}"
        msg_log+=" successfully added to nodeinfo table"
        msg.append(msg_log)

    module.exit_json(changed=True, msg='\n'.join(msg))

if __name__ == "__main__":
    main()
