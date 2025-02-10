# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import subprocess

sys.path.append('/opt/omnia/shared_libraries/provision/db_operations')
import omniadb_connection

switch_ip = sys.argv[1]
switch_ports = sys.argv[2]
node_obj = ""


def check_switch_table():
    # Check if cluster.nodeinfo has valid input for switch_based entry
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = '''select max(id) from cluster.nodeinfo where switch_port is not NULL'''
    cursor.execute(sql)
    switch_op = cursor.fetchone()
    if switch_op[0] is None:
        sys.exit("Nodeinfo table doesnt contain any input")
    conn.close()
    return "true"


def delete_node_object(nodename):
    # Delete the entry from /etc/hosts
    print("hello=", nodename)
    command = f"/opt/xcat/sbin/makehosts -d {nodename}"
    temp = subprocess.run([f'{command}'], shell=True)

    # Delete the nodes from xcat
    command = f"/opt/xcat/bin/rmdef {nodename}"
    print(command)
    temp = subprocess.run([f'{command}'], shell=True)

    # Run DHCP and dns
    command = f"/opt/xcat/sbin/makedhcp -a"
    temp = subprocess.run([f'{command}'], shell=True)

    command = f"/opt/xcat/sbin/makedhcp -n"
    temp = subprocess.run([f'{command}'], shell=True)

    command = f"/opt/xcat/sbin/makedns -n"
    temp = subprocess.run([f'{command}'], shell=True)


def delete_switch_db_details():
    switch_op = check_switch_table()
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    ports = switch_ports.split(',')
    sql = '''select switch_name from cluster.switchinfo where switch_ip= '{switch_ip}' '''.format(switch_ip=switch_ip)
    cursor.execute(sql)
    switch_name = cursor.fetchone()[0]
    print(ports)
    if switch_op == "true":
        for i in range(0, len(ports)):
            if '-' in ports[i]:
                start_port = int(ports[i].split('-')[0])
                end_port = int(ports[i].split('-')[1]) + 1

                for j in range(start_port, end_port):
                    port = str(j)
                    sql = '''select exists(select switch_port from cluster.nodeinfo where switch_port = '{switch_port_key}' and switch_name='{switch_v3_name}')'''.format(
                        switch_port_key=port, switch_v3_name=switch_name)
                    cursor.execute(sql)
                    output = cursor.fetchone()[0]
                    if output:
                        sql = '''select node from cluster.nodeinfo where switch_port = '{switch_port_key}' and switch_name='{switch_v3_name}' '''.format(
                            switch_port_key=port, switch_v3_name=switch_name)
                        cursor.execute(sql)
                        node_obj = cursor.fetchone()[0]

                        sql = '''delete from cluster.nodeinfo where switch_port = '{switch_port_key}' and switch_name='{switch_v3_name}' '''.format(
                            switch_port_key=port, switch_v3_name=switch_name)
                        cursor.execute(sql)

                        delete_node_object(node_obj)

                    else:
                        print("switch_port=", port, " for switch_ip=", switch_ip, "not present in the DB")

            else:
                port = str(ports[i])
                print(port)
                sql = '''select exists(select switch_port from cluster.nodeinfo where switch_port = '{switch_port_key}' and switch_name='{switch_v3_name}')'''.format(
                    switch_port_key=port, switch_v3_name=switch_name)
                cursor.execute(sql)
                output = cursor.fetchone()[0]

                if output:
                    sql = '''select node from cluster.nodeinfo where switch_port = '{switch_port_key}' and switch_name='{switch_v3_name}' '''.format(
                        switch_port_key=port, switch_v3_name=switch_name)
                    cursor.execute(sql)
                    node_obj = cursor.fetchone()[0]

                    sql = '''delete from cluster.nodeinfo where switch_port = '{switch_port_key}' and switch_name='{switch_v3_name}' '''.format(
                        switch_port_key=port, switch_v3_name=switch_name)
                    cursor.execute(sql)

                    delete_node_object(node_obj)
                    print(node_obj)

                else:
                    print("switch_port=", port, "for switch_ip=", switch_ip, "not present in the DB")


delete_switch_db_details()
