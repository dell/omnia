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

import sys
import ipaddress

db_path = sys.argv[12]
sys.path.insert(0, db_path)
import omniadb_connection

mtms_db_path = sys.argv[13]
sys.path.insert(0, mtms_db_path)
import correlation_admin_bmc
import modify_network_details

# Fetch input arguments
switch_v3_ip = ipaddress.IPv4Address(sys.argv[1])
switch_v3_ports = sys.argv[2]
bmc_static_range = sys.argv[3]
bmc_static_subnet = sys.argv[4]
node_name = sys.argv[5]
domain_name = sys.argv[6]
admin_static_range = sys.argv[7]
admin_subnet = sys.argv[8]
netmask_bits = sys.argv[9]
correlation_status = sys.argv[10].lower()
uncorrelated_admin_start_ip = ipaddress.IPv4Address(sys.argv[11])
discovery_mechanism = "switch_based"
bmc_mode = "static"

admin_static_start_range = ipaddress.IPv4Address(admin_static_range.split('-')[0])
admin_static_end_range = ipaddress.IPv4Address(admin_static_range.split('-')[1])
bmc_static_start_ip = ipaddress.IPv4Address(bmc_static_range.split('-')[0])
bmc_static_end_ip = ipaddress.IPv4Address(bmc_static_range.split('-')[1])

def check_switch_table(cursor):
    """
	Checks if the switchinfo table in the cluster schema contains any entries.

	Parameters:
	- cursor (psycopg2.extensions.cursor): The database cursor.

	Returns:
	- str: "true" if the switchinfo table contains entries, "false" otherwise.
	"""

    sql = '''select max(id) from cluster.switchinfo'''
    cursor.execute(sql)
    switch_op = cursor.fetchone()
    if switch_op[0] is None:
        sys.exit("Switch table doesnt contain any input")
    return "true"

def check_presence_switch_port(cursor,switch_v3_name,switch_v3_port):
    """
	Checks the presence of a switch port in the cluster.nodeinfo table.

	Parameters:
	- cursor (psycopg2.extensions.cursor): The database cursor.
	- switch_v3_name (str): The name of the switch.
	- switch_v3_port (str): The port number of the switch.

	Returns:
	- bool: True if the switch port is present in the cluster.nodeinfo table, False otherwise.
	"""

    sql = f"select exists(select switch_port from cluster.nodeinfo where switch_port = '{switch_v3_port}' and switch_name='{switch_v3_name}')"
    cursor.execute(sql)
    output = cursor.fetchone()[0]
    return output

def insert_switch_details(cursor,switch_v3_name,switch_v3_port):
    """
    Inserts switch details into the cluster.nodeinfo table.

    Parameters:
        cursor (psycopg2.extensions.cursor): The database cursor.
        switch_v3_name (str): The name of the switch.
        switch_v3_port (str): The port of the switch.

    Returns:
        None
    """
    sql = '''select id from cluster.nodeinfo ORDER BY id DESC LIMIT 1'''
    cursor.execute(sql)
    temp = cursor.fetchone()
    if temp[0] is None:
        temp = [0]
    initial_id = temp[0]
    ip_count = int(temp[0]) - int(initial_id)
    count = '%05d' % (int(temp[0]) + 1)
    node = node_name + str(count)
    host_name = node_name + str(count) + "." + domain_name

    # Set bmc_ip
    bmc_ip = modify_network_details.reassign_bmc_ip(cursor,bmc_static_start_ip,bmc_static_end_ip)

    # Set admin_ip when correlation_status is true
    if correlation_status == "true":
        admin_ip = correlation_admin_bmc.correlation_bmc_to_admin(str(bmc_ip), admin_subnet, netmask_bits)
        if admin_static_start_range <= admin_ip <= admin_static_end_range:
            output = modify_network_details.check_presence_admin_ip(cursor, admin_ip)
            if not output:
                omniadb_connection.insert_node_info(None, node, host_name, None, admin_ip, bmc_ip, discovery_mechanism, bmc_mode, switch_v3_ip, switch_v3_name, switch_v3_port)
            elif output:
                admin_ip = modify_network_details.cal_uncorrelated_admin_ip(cursor, uncorrelated_admin_start_ip, admin_static_start_range,admin_static_end_range,discovery_mechanism)
                omniadb_connection.insert_node_info(None, node, host_name, None, admin_ip, bmc_ip, discovery_mechanism, bmc_mode, switch_v3_ip, switch_v3_name, switch_v3_port)
        else:
            admin_ip = modify_network_details.cal_uncorrelated_admin_ip(cursor, uncorrelated_admin_start_ip, admin_static_start_range,admin_static_end_range,discovery_mechanism)
            omniadb_connection.insert_node_info(None, node, host_name, None, admin_ip, bmc_ip, discovery_mechanism, bmc_mode, switch_v3_ip, switch_v3_name, switch_v3_port)
    # Set admin_ip when correlation_status is false
    elif correlation_status == "false":
        admin_ip = modify_network_details.cal_uncorrelated_admin_ip(cursor, uncorrelated_admin_start_ip, admin_static_start_range,admin_static_end_range,discovery_mechanism)
        omniadb_connection.insert_node_info(None, node, host_name, None, admin_ip, bmc_ip, discovery_mechanism, bmc_mode, switch_v3_ip, switch_v3_name, switch_v3_port)

def main():
    """
    The main function of the program.

    This function establishes a connection with the database, retrieves the cursor, and performs the following tasks:
    - Checks if the cluster.switchinfo table has any entry.
    - If the table has an entry, it retrieves the switch name from the cluster.switchinfo table.
    - It splits the switch_v3_ports string by commas and iterates over each port.
    - If the port is a range (e.g., "1-5"), it iterates over the range and checks if the switch port is already present in the cluster.nodeinfo table.
    - If the switch port is not present, it inserts the switch details into the cluster.nodeinfo table.
    - If the port is not a range, it checks if the switch port is already present in the cluster.nodeinfo table.
    - If the switch port is not present, it inserts the switch details into the cluster.nodeinfo table.

    Parameters:
        None

    Returns:
        None
    """
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()

    existing_ports = []
    new_added_ports = []

    # Check cluster.switchinfo table has any entry or not
    switch_output = check_switch_table(cursor)
    ports = switch_v3_ports.split(',')

    # Fetch switch name from cluster.switchinfo table
    sql = f"select switch_name from cluster.switchinfo where switch_ip= '{switch_v3_ip}'"
    cursor.execute(sql)
    switch_v3_name = cursor.fetchone()[0]

    # Update DB when atleast 1 entry present in cluster.switchinfo table
    if switch_output:
        for i in range(0, len(ports)):
            if '-' in ports[i]:
                start_port = int(ports[i].split('-')[0])
                end_port = int(ports[i].split('-')[1])+1
                print("with -:", start_port, end_port)

                for j in range(start_port, end_port):
                    new_added_ports.append(j)
                    switch_v3_port = str(j)
                    
                    # Check node details for the switch port already added
                    output = check_presence_switch_port(cursor,switch_v3_name,switch_v3_port)

                    if not output:
                        insert_switch_details(cursor,switch_v3_name,switch_v3_port)
                    if output:
                        existing_ports.append(j)
                        print(existing_ports, "for", switch_v3_name, "already exists in the DB")

            if '-' not in ports[i]:
                new_added_ports.append(ports[i])
                switch_v3_port = str(ports[i])

                # Check node details for the switch port already added
                output = check_presence_switch_port(cursor,switch_v3_name,switch_v3_port)

                if not output:
                    insert_switch_details(cursor,switch_v3_name,switch_v3_port)
                if output:
                    existing_ports.append(ports[i])
                    print(existing_ports, "for", switch_v3_name, "already exists in the DB")

    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
