# Copyright 2023 Dell Inc. or its subsidiaries. All Rights Reserved.
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

admin_nic_ip = sys.argv[1]
network_interface_type = sys.argv[2]
pxe_mac_address = sys.argv[3]
bmc_nic_ip = sys.argv[4]
cp_hostname = sys.argv[5]
node_name = "control_plane"
admin_nic_ip = ipaddress.IPv4Address(admin_nic_ip)
bmc_nic_ip = ipaddress.IPv4Address(bmc_nic_ip)


def cp_details_db():
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = '''select admin_mac from cluster.nodeinfo where admin_mac= '{pxe_mac_address}' '''.format(
        pxe_mac_address=pxe_mac_address)
    cursor.execute(sql)
    pxe_mac_op = cursor.fetchone()
    if pxe_mac_op is None:
        omniadb_connection.insert_cp_details_db(cursor, node_name, network_interface_type, bmc_nic_ip, admin_nic_ip, pxe_mac_address, cp_hostname)

    conn.close()
cp_details_db()
