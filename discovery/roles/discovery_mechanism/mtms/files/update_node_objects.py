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

import subprocess
import sys

db_path = sys.argv[2]
sys.path.insert(0, db_path)
import omniadb_connection

node_obj_nm = []
groups_static = "all,bmc,bmc_static"
groups_dynamic = "all,bmc,bmc_dynamic"
groups_discover = "all,bmc,bmc_discover"
chain_setup = "runcmd=bmcsetup"
os_name = sys.argv[1]
chain_os = f"osimage={os_name}"
discovery_mechanism = "mtms"


def get_node_obj():
    """
       Get a list of node objects present in Omnia Infrastrcuture Management (OIM) node
       Returns:
         formed a list of node object names
    """
    command = "/opt/xcat/bin/lsdef"
    node_objs = subprocess.run(command.split(), capture_output=True)
    temp = str(node_objs.stdout).split('\n')
    for i in range(0, len(temp) - 1):
        node_obj_nm.append(temp[i].split(' ')[0])

    update_node_obj_nm()


def update_node_obj_nm():
    """
       Update the node objects with proper details as per their bmc mode
       Returns:
         Updated node objects with proper details attached to it.
    """

    # Establish a connection with omniadb
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = """select service_tag from cluster.nodeinfo where discovery_mechanism = %s"""
    cursor.execute(sql, (discovery_mechanism,))
    serial_output = cursor.fetchall()
    for i in range(0, len(serial_output)):
        if serial_output[i][0] is not None:
            serial_output[i] = str(serial_output[i][0]).lower()
    for i in range(0, len(serial_output)):
        print(serial_output[i])
        if serial_output[i][0] is not None:
            serial_output[i] = serial_output[i].upper()
            sql = "SELECT node FROM cluster.nodeinfo WHERE service_tag = '" + serial_output[i] + "'"
            cursor.execute(sql)
            node_name = cursor.fetchone()
            sql = "select admin_ip from cluster.nodeinfo where service_tag = '" + serial_output[i] + "'"
            cursor.execute(sql)
            admin_ip = cursor.fetchone()
            sql = "select bmc_mode from cluster.nodeinfo where service_tag = '" + serial_output[i] + "'"
            cursor.execute(sql)
            mode = cursor.fetchone()[0]

            if mode is None:
                print("No device is found!")
            if mode == "static":
                command = ["/opt/xcat/bin/chdef", node_name[0], f"ip={admin_ip[0]}", f"groups={groups_static}",
                           f"chain={chain_setup},{chain_os}"]
                subprocess.run(command)
            if mode == "discovery":
                command = ["/opt/xcat/bin/chdef", node_name[0], f"ip={admin_ip[0]}", f"groups={groups_discover}",
                           f"chain={chain_setup},{chain_os}"]
                subprocess.run(command)
            if mode == "dynamic":
                sql = "select bmc_ip from cluster.nodeinfo where service_tag = '" + serial_output[i] + "'"
                cursor.execute(sql)
                bmc_ip = cursor.fetchone()
                command = ["/opt/xcat/bin/chdef", node_name[0], f"ip={admin_ip[0]}", f"groups={groups_dynamic}",
                           f"chain={chain_setup},{chain_os}"]
                subprocess.run(command)
                command = ["/opt/xcat/bin/chdef", node_name[0], f" bmc={bmc_ip[0]}"]
                subprocess.run(command)

    cursor.close()
    conn.close()


get_node_obj()
