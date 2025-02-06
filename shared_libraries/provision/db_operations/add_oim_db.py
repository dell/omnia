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
import omniadb_connection
import ipaddress

num_args = len(sys.argv) - 1
admin_nic_ip = sys.argv[1]
network_interface_type = sys.argv[2]
pxe_mac_address = sys.argv[3]
oim_hostname = sys.argv[4]
bmc_default = "0.0.0.0"
if num_args == 5:
    bmc_nic_ip = sys.argv[5]
else:
    bmc_nic_ip = "0.0.0.0"

node_name = "oim"
admin_nic_ip = ipaddress.IPv4Address(admin_nic_ip)
bmc_nic_ip = ipaddress.IPv4Address(bmc_nic_ip)


def oim_details_db():
    """
    Connects to the database, executes a query to check if the pxe_mac_address exists in the cluster.nodeinfo table,
    and then inserts a new row for OIM node if the pxe_mac_address is not found.

    Parameters:
        None

    Returns:
        None
    """
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = "select admin_mac from cluster.nodeinfo where admin_mac=%s"
    cursor.execute(sql, (pxe_mac_address,))
    pxe_mac_op = cursor.fetchone()
    if pxe_mac_op is None:
            if str(bmc_nic_ip) == "0.0.0.0":
                omniadb_connection.insert_node_info(None, node_name, oim_hostname, pxe_mac_address, admin_nic_ip, None, None, None, None, None, None)
            else:
                omniadb_connection.insert_node_info(None, node_name, oim_hostname, pxe_mac_address, admin_nic_ip, bmc_nic_ip, None, None, None, None, None)


oim_details_db()