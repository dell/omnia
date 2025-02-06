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

import sys, os
import pandas as pd
import ipaddress

db_path = sys.argv[1]
sys.path.insert(0, db_path)

import omniadb_connection

pxe_mapping_path = os.path.abspath(sys.argv[2])
domain_name = sys.argv[3]
discovery_mechanism = "mapping"
admin_mac = []
hostname = []
admin_ip = []
bmc_ip = []
nan = float('nan')


def not_nan_val(ip):
    """
    Check if the given IP address is not NaN.

    Args:
        ip (Any): The IP address to check.

    Returns:
        bool: True if the IP address is not NaN, False otherwise.
    """
    if pd.notna(ip):
        ipaddress.ip_address(ip)
        return True
    else:
        return False


def mapping_file_db_update():
    """
    Updates the database with the information from a mapping file.

    This function reads a mapping file containing information about nodes, such as service tags, hostnames,
    admin MAC addresses, admin IP addresses, and BMC IP addresses. It then connects to the database and checks
    if the service tags already exist in the table. If a service tag is not found, it inserts the information
    into the table. If a service tag is found, it appends the admin MAC address to a list.

    Parameters:
        None

    Returns:
        None
    """
    data = pd.read_csv(pxe_mapping_path)
    admin_mac = data['ADMIN_MAC'].tolist()
    hostname = data['HOSTNAME'].tolist()
    admin_ip = data['ADMIN_IP'].tolist()
    bmc_ip = data['BMC_IP'].tolist()
    service_tag = data['SERVICE_TAG'].tolist()
    existing_mac = []

    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()

    for key in range(0, len(admin_mac)):
        temp_mac = admin_mac[key]
        temp_service_tag = service_tag[key]
        # Check if the mac address already exists in the table
        query = "SELECT EXISTS(SELECT service_tag FROM cluster.nodeinfo WHERE service_tag=%s)"
        cursor.execute(query, (temp_service_tag,))
        output = cursor.fetchone()[0]
        fqdn_hostname = hostname[key] + "." + domain_name
        node = hostname[key]
        temp_admin_ip = admin_ip[key]
        temp_service_tag = service_tag[key]

        # Check if bmc_ip/ ib_ip is NAN value
        temp_bmc_ip = bmc_ip[key]
        bmc_out = not_nan_val(temp_bmc_ip)
        if not bmc_out:
            temp_bmc_ip = None

        if output is False:
            omniadb_connection.insert_node_info(temp_service_tag, node, fqdn_hostname, temp_mac, temp_admin_ip,
                                                temp_bmc_ip, discovery_mechanism, None, None, None, None)
        else:
            existing_mac.append(admin_mac[key])
            sys.stdout.write(admin_mac[key] + " already present in DB.")

    conn.close()


mapping_file_db_update()