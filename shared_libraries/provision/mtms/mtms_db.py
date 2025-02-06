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
#  limitations under the License


import ipaddress
import sys, os
import warnings
import correlation_admin_bmc
import modify_network_details

db_path = sys.argv[15]
sys.path.insert(0, db_path)

import omniadb_connection

discovery_ranges = sys.argv[1]
bmc_static_range = sys.argv[2]
bmc_static_subnet = sys.argv[3]
bmc_dynamic_range = sys.argv[4]
bmc_dynamic_subnet = bmc_static_subnet
static_stanza_path = os.path.abspath(sys.argv[5])
dynamic_stanza_path = os.path.abspath(sys.argv[6])
node_name = sys.argv[7]
domain_name = sys.argv[8]
admin_static_range = sys.argv[9]
admin_subnet = sys.argv[10]
netmask_bits = sys.argv[11]
discover_stanza_path = os.path.abspath(sys.argv[12])
correlation_status = sys.argv[13]
uncorrelated_admin_start_ip = ipaddress.IPv4Address(sys.argv[14])
discovery_mechanism = "mtms"
bmc_mode = "static"
admin_static_start_range = ipaddress.IPv4Address(admin_static_range.split('-')[0])
admin_static_end_range = ipaddress.IPv4Address(admin_static_range.split('-')[1])


def update_db():
    """
    Updates the database based on the given parameters.

    This function performs the following tasks:
    1. Creates a connection to the database.
    2. Retrieves the cursor object from the connection.
    3. Checks if the `discovery_ranges` variable is not equal to "0.0.0.0".
    4. If the condition is true, it extracts the serial and bmc information from the `discover_stanza_path` file.
    5. Iterates over the serial and bmc information and performs the following actions:
       - Executes a SQL query to check if the serial exists in the `cluster.nodeinfo` table.
       - Checks if the bmc IP is present in the database.
       - If both conditions are false, it performs the following actions:
         - Increments the node ID and generates the node and host names.
         - Updates the stanza file with the serial and node information.
         - Calculates the admin IP based on the discovery mechanism.
         - Inserts the node information into the `cluster.nodeinfo` table.
       - If the conditions are true, it prints a warning message and the serial.

    6. If the `bmc_static_range` variable is not empty, it performs the following actions:
       - Extracts the serial and bmc information from the `static_stanza_path` file.
       - Iterates over the serial and bmc information and performs the following actions:
         - Executes a SQL query to check if the serial exists in the `cluster.nodeinfo` table.
         - Checks if the bmc IP is present in the database.
         - If both conditions are false, it performs the following actions:
           - Increments the node ID and generates the node and host names.
           - Updates the stanza file with the serial and node information.
           - Calculates the admin IP based on the correlation between the bmc and admin subnet.
           - Checks if the admin IP is present in the database.
           - If the admin IP is not present, it inserts the node information into the `cluster.nodeinfo` table.
           - If the admin IP is present, it calculates the uncorrelated admin IP and inserts the node information.
         - If the conditions are true, it prints a warning message and the serial.

    7. Closes the cursor and the database connection.

    Parameters:
    None

    Returns:
    None
    """

    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()

    # Without correlation
    if discovery_ranges != "0.0.0.0":
        temp = modify_network_details.extract_serial_bmc(discover_stanza_path)
        bmc = temp[0]
        serial = temp[1]
        for key in range(0, len(serial)):
            sql = f"select exists(select service_tag from cluster.nodeinfo where service_tag='{serial[key]}')"
            cursor.execute(sql)
            output = cursor.fetchone()[0]
            bmc_output = modify_network_details.check_presence_bmc_ip(cursor, bmc[key])
            if not bmc_output and not output:
                sql = '''select id from cluster.nodeinfo ORDER BY id DESC LIMIT 1'''
                cursor.execute(sql)
                temp = cursor.fetchone()
                if temp is None:
                    temp = [0]
                count = '%05d' % (int(temp[0]) + 1)
                node = node_name + str(count)
                host_name = node_name + str(count) + "." + domain_name
                modify_network_details.update_stanza_file(serial[key].lower(), node, discover_stanza_path)

                admin_ip = modify_network_details.cal_uncorrelated_admin_ip(cursor, uncorrelated_admin_start_ip,
                                                                            admin_static_start_range,
                                                                            admin_static_end_range, discovery_mechanism)
                omniadb_connection.insert_node_info(serial[key], node, host_name, None, admin_ip,
                                                    bmc[key], discovery_mechanism, bmc_mode, None, None, None)
            else:
                warnings.warn('Node already present in the database')
                print(serial[key]+"\n")

    if bmc_static_range != "":
        temp = modify_network_details.extract_serial_bmc(static_stanza_path)
        bmc = temp[0]
        serial = temp[1]
        for key in range(0, len(serial)):
            sql = f"select exists(select service_tag from cluster.nodeinfo where service_tag='{serial[key]}')"
            cursor.execute(sql)
            output = cursor.fetchone()[0]
            bmc_output = modify_network_details.check_presence_bmc_ip(cursor, bmc[key])
            if not bmc_output and not output:
                sql = '''select id from cluster.nodeinfo ORDER BY id DESC LIMIT 1'''
                cursor.execute(sql)
                temp = cursor.fetchone()
                if temp is None:
                    temp = [0]
                count = '%05d' % (int(temp[0]) + 1)
                node = node_name + str(count)
                host_name = node_name + str(count) + "." + domain_name
                modify_network_details.update_stanza_file(serial[key].lower(), node, static_stanza_path)
                admin_ip = correlation_admin_bmc.correlation_bmc_to_admin(bmc[key], admin_subnet, netmask_bits)
                if admin_static_start_range <= admin_ip <= admin_static_end_range:
                    output = modify_network_details.check_presence_admin_ip(cursor, admin_ip)
                    if not output:
                        omniadb_connection.insert_node_info(serial[key], node, host_name, None, admin_ip,
                                                            bmc[key], discovery_mechanism, bmc_mode, None, None,
                                                            None)
                    elif output:
                        admin_ip = modify_network_details.cal_uncorrelated_admin_ip(cursor,
                                                                                    uncorrelated_admin_start_ip,
                                                                                    admin_static_start_range,
                                                                                    admin_static_end_range,
                                                                                    discovery_mechanism)
                        omniadb_connection.insert_node_info(serial[key], node, host_name, None, admin_ip,
                                                            bmc[key], discovery_mechanism, bmc_mode, None, None,
                                                            None)
                else:
                    admin_ip = modify_network_details.cal_uncorrelated_admin_ip(cursor, uncorrelated_admin_start_ip,
                                                                                admin_static_start_range,
                                                                                admin_static_end_range,
                                                                                discovery_mechanism)
                    omniadb_connection.insert_node_info(serial[key], node, host_name, None, admin_ip,
                                                        bmc[key], discovery_mechanism, bmc_mode, None, None,
                                                        None)
            else:
                warnings.warn('Node already present in the database')
                print(serial[key])

        cursor.close()
        conn.close()


update_db()
