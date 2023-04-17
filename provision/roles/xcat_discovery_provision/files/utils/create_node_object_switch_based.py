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

import omniadb_connection
import sys
import subprocess

groups_switch_based = '"switch_based,all"'

def create_node_object(conn):

    cursor = conn.cursor()
    sql = '''select switch_name,switch_port from cluster.nodeinfo where switch_port is not NULL'''
    cursor.execute(sql)
    switch_port_output = cursor.fetchall()

    for i in range(0, len(switch_port_output)):
        if switch_port_output[i][0] is not None:

            sql = '''select node,admin_ip,bmc_ip,switch_name,switch_port from cluster.nodeinfo where switch_port='{switch_port}' and switch_name='{switch_name}' '''.format(switch_name=switch_port_output[i][0],switch_port=switch_port_output[i][1])
            cursor.execute(sql)
            row_output = cursor.fetchone()

            command = f"chdef {row_output[0]} groups={groups_switch_based} mgt=ipmi cons=ipmi ip={row_output[1]} bmc={row_output[2]} netboot=xnba installnic=mac primarynic=mac switch={row_output[3]} switchport={row_output[4]}"
            create_node = subprocess.run([f'{command}'], shell=True)

            print(f"Created node object with name {row_output[0]}")

    cursor.close()

def main():

   conn = omniadb_connection.create_connection()
   create_node_object(conn)
   conn.close()

if __name__ == '__main__':
    main()
