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
"""
This module contains functions for inserting OIM details into the database.
"""

import sys
import ipaddress
import omniadb_connection

NUM_ARGS = len(sys.argv) - 1
ADMIN_NIC_IP = sys.argv[1]
NETWORK_INTERFACE_TYPE = sys.argv[2]
PXE_MAC_ADDRESS = sys.argv[3]
OIM_HOSTNAME = sys.argv[4]
BMC_DEFAULT = "0.0.0.0"
if NUM_ARGS == 5:
    BMC_NIC_IP = sys.argv[5]
else:
    BMC_NIC_IP = "0.0.0.0"

NODE_NAME = "oim"
ADMIN_NIC_IP = ipaddress.IPv4Address(ADMIN_NIC_IP)
BMC_NIC_IP = ipaddress.IPv4Address(BMC_NIC_IP)

def oim_details_db():
    """
    Connects to the database, executes a query to check if the PXE_MAC_ADDRESS exists in
    the cluster.nodeinfo table, and then inserts a new row for OIM node if the
    PXE_MAC_ADDRESS is not found.

    Parameters:
        None

    Returns:
        None
    """
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = "select admin_mac from cluster.nodeinfo where admin_mac=%s or node=%s"
    cursor.execute(sql, (PXE_MAC_ADDRESS, NODE_NAME))
    pxe_mac_op = cursor.fetchone()
    if pxe_mac_op is None:
        if str(BMC_NIC_IP) == "0.0.0.0":
            omniadb_connection.insert_node_info(
                None, NODE_NAME, OIM_HOSTNAME, PXE_MAC_ADDRESS, ADMIN_NIC_IP, None,
                None, None, None, None, None, None, None, None, None, None
            )
        else:
            omniadb_connection.insert_node_info(
                None, NODE_NAME, OIM_HOSTNAME, PXE_MAC_ADDRESS, ADMIN_NIC_IP, BMC_NIC_IP,
                None, None, None, None, None, None, None, None, None, None
            )

oim_details_db()
