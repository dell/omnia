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

import re
import sys, os
import warnings
import ipaddress
import correlation_admin_bmc
import modify_network_details

db_path = sys.argv[12]
sys.path.insert(0, db_path)

import omniadb_connection

dynamic_stanza_path = os.path.abspath(sys.argv[1])
node_name = sys.argv[2]
domain_name = sys.argv[3]
pxe_subnet = sys.argv[4]
bmc_static_ranges = sys.argv[5]
bmc_dynamic_ranges = sys.argv[6]
reassignment_status = sys.argv[7]
correlation_status = sys.argv[8]
uncorrelated_admin_start_ip = ipaddress.IPv4Address(sys.argv[9])
netmask_bits = sys.argv[10]
admin_static_range = sys.argv[11]
admin_static_start_range = ipaddress.IPv4Address(admin_static_range.split('-')[0])
admin_static_end_range = ipaddress.IPv4Address(admin_static_range.split('-')[1])
bmc_static_start_ip = ipaddress.IPv4Address(bmc_static_ranges.split('-')[0])
bmc_static_end_ip = ipaddress.IPv4Address(bmc_static_ranges.split('-')[1])
discovery_mechanism = "mtms"
bmc_mode = "dynamic"


def update_db():
    """
	Update the database with new node information.

	This function establishes a connection with omniadb and performs the following tasks:
	- Extracts serial and bmc information from the dynamic stanza path.
	- Checks if the serial exists in the cluster.nodeinfo table.
	- If not, it generates a new node name and host name based on the node_name and domain_name.
	- It updates the stanza file with the new serial, node, and dynamic_stanza_path.
	- If reassignment_status is True and correlation_status is True, it reassigns the bmc_ip and calculates the admin_ip.
	- If reassignment_status is True and correlation_status is False, it reassigns the bmc_ip and calculates the admin_ip.
	- If reassignment_status is False, it calculates the admin_ip.
	- It inserts the node information into the cluster.nodeinfo table.

	Parameters:
	None

	Returns:
	None
	"""

    serial = []
    bmc = []
    # Establish a connection with omniadb
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    if bmc_dynamic_ranges != "":
        temp = modify_network_details.extract_serial_bmc(dynamic_stanza_path)
        bmc = temp[0]
        serial = temp[1]
    for key in range(0, len(serial)):
        sql = f"select exists(select service_tag from cluster.nodeinfo where service_tag='{serial[key]}')"
        cursor.execute(sql)
        output = cursor.fetchone()[0]
        if not output:
            sql = '''select id from cluster.nodeinfo ORDER BY id DESC LIMIT 1'''
            cursor.execute(sql)
            temp = cursor.fetchone()
            if temp is None:
                temp = [0]
            count = '%05d' % (int(temp[0]) + 1)
            node = node_name + str(count)
            host_name = node_name + str(count) + "." + domain_name
            modify_network_details.update_stanza_file(serial[key].lower(), node, dynamic_stanza_path)
            if reassignment_status and correlation_status:
                bmc_ip = modify_network_details.reassign_bmc_ip(cursor,bmc_static_start_ip,bmc_static_end_ip)
                admin_ip = correlation_admin_bmc.correlation_bmc_to_admin(str(bmc_ip), pxe_subnet, netmask_bits)
                if admin_static_start_range <= admin_ip <= admin_static_end_range:
                    output = modify_network_details.check_presence_admin_ip(cursor, admin_ip)
                    if not output:
                        omniadb_connection.insert_node_info(serial[key], node, host_name, None, admin_ip,
                                                            bmc_ip, discovery_mechanism, bmc_mode, None, None,
                                                            None)
                    elif output:
                        admin_ip = modify_network_details.cal_uncorrelated_admin_ip(cursor, uncorrelated_admin_start_ip,admin_static_start_range,admin_static_end_range,discovery_mechanism)
                        omniadb_connection.insert_node_info(serial[key], node, host_name, None, admin_ip,
                                                            bmc_ip, discovery_mechanism, bmc_mode, None, None,
                                                            None)
            elif reassignment_status and not correlation_status:
                bmc_ip = modify_network_details.reassign_bmc_ip(cursor,bmc_static_start_ip,bmc_static_end_ip)
                admin_ip = modify_network_details.cal_uncorrelated_admin_ip(cursor, uncorrelated_admin_start_ip,admin_static_start_range,admin_static_end_range,discovery_mechanism)
                omniadb_connection.insert_node_info(serial[key], node, host_name, None, admin_ip,
                                                    bmc_ip, discovery_mechanism, bmc_mode, None, None,
                                                    None)
            elif not reassignment_status:
                admin_ip =modify_network_details. cal_uncorrelated_admin_ip(cursor, uncorrelated_admin_start_ip,admin_static_start_range,admin_static_end_range,discovery_mechanism)
                omniadb_connection.insert_node_info(serial[key], node, host_name, None, admin_ip,
                                                    bmc[key], discovery_mechanism, bmc_mode, None, None,
                                                    None)

        else:
            warnings.warn('Node already present in the database')
            print(serial[key])
    cursor.close()
    conn.close()


update_db()
