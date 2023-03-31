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

switch_v3_ip = sys.argv[1]
switch_v3_ports = sys.argv[2]
bmc_start_range = sys.argv[3]
bmc_end_range = sys.argv[4]
admin_start_range = sys.argv[5]
admin_end_range = sys.argv[6]
ib_status = sys.argv[7]
ib_start_range = sys.argv[8]
ib_end_range = sys.argv[9]
node_name = sys.argv[10]
domain_name = sys.argv[11]

switch_v3_ip = ipaddress.IPv4Address(switch_v3_ip)
bmc_start_range = ipaddress.IPv4Address(bmc_start_range)
bmc_end_range = ipaddress.IPv4Address(bmc_end_range)
admin_start_range = ipaddress.IPv4Address(admin_start_range)
admin_end_range = ipaddress.IPv4Address(admin_end_range)
ib_start_range = ipaddress.IPv4Address(ib_start_range)
ib_end_range = ipaddress.IPv4Address(ib_end_range)


def check_switch_table():
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = '''select max(id) from cluster.switchinfo'''
    cursor.execute(sql)
    switch_op = cursor.fetchone()
    if switch_op[0] is None:
        sys.exit("Switch table doesnt contain any input")
    conn.close()
    return "true"


def switch_based_bmc_details(ip_count):
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = '''select max(bmc_ip) from cluster.nodeinfo where switch_port is not NULL'''
    cursor.execute(sql)
    temp_bmc = cursor.fetchone()[0]
    if temp_bmc is None:
        temp_bmc = bmc_start_range - 1
    if bmc_start_range + ip_count > bmc_end_range:
        sys.exit('IP range has exceeded the provided range. Please provide proper range')
    temp_bmc = ipaddress.IPv4Address(temp_bmc) + 1
    conn.close()
    return temp_bmc


def switch_based_admin_details(temp, initial_id):
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = '''select max(admin_ip) from cluster.nodeinfo where switch_port is not NULL'''
    cursor.execute(sql)
    temp_admin = cursor.fetchone()[0]
    if temp_admin is None:
        temp_admin = admin_start_range - 1
    temp_admin = ipaddress.IPv4Address(temp_admin) + 1
    conn.close()
    return temp_admin


def switch_based_ib_details(temp, initial_id, temp_admin):
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = '''select max(ib_ip) from cluster.nodeinfo where switch_port is not NULL '''
    cursor.execute(sql)
    temp_ib = cursor.fetchone()[0]
    if temp_ib is None:
        temp_ib = ib_start_range - 1
    ib_ip=str(temp_ib).split('.')[0] + '.' + str(temp_ib).split('.')[1] + '.' + str(temp_admin).split('.')[2] + '.' + str(temp_admin).split('.')[3]
    conn.close()
    return ib_ip


def insert_switch_details():
    existing_ports = []
    new_added_ports = []
    switch_op = check_switch_table()
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    ports = switch_v3_ports.split(',')
    sql = '''select switch_name from cluster.switchinfo where switch_ip= '{switch_v3_ip}' '''.format(switch_v3_ip = switch_v3_ip)
    cursor.execute(sql)
    switch_v3_name = cursor.fetchone()[0]
    if switch_op == "true":
        for i in range(0, len(ports)):
            if '-' in ports[i]:
                start_port = int(ports[i].split('-')[0])
                end_port = int(ports[i].split('-')[1])+1
                print("with -:", start_port, end_port)

                for j in range(start_port, end_port):
                    new_added_ports.append(j)
                    port = str(j)
                    sql = '''select exists(select switch_port from cluster.nodeinfo where switch_port = '{switch_port_key}' and switch_name='{switch_v3_name}')'''.format(
                        switch_port_key=port, switch_v3_name=switch_v3_name)
                    cursor.execute(sql)
                    output = cursor.fetchone()[0]

                    if not output:
                        sql = '''select max(id) from cluster.nodeinfo where switch_port is not NULL'''
                        cursor.execute(sql)
                        temp = cursor.fetchone()
                        if temp[0] is None:
                            temp = [0]
                        initial_id = temp[0]
                        ip_count = int(temp[0]) - int(initial_id)
                        count = '%05d' % (int(temp[0]) + 1)
                        node = node_name + str(count)
                        host_name = node_name + str(count) + "." + domain_name

                        # BMC IP details
                        temp_bmc = switch_based_bmc_details(ip_count)

                        # Admin IP details
                        temp_admin = switch_based_admin_details(temp, initial_id)

                        # IB IP details
                        if ib_status == "True":
                            temp_ib = switch_based_ib_details(temp, initial_id, temp_admin)
                        else:
                            temp_ib = None

                        # Insert details in DB
                        omniadb_connection.insert_switch_based_server(cursor, temp_bmc, temp_admin, temp_ib, node, host_name, switch_v3_ip, switch_v3_name, j,ib_status)

                    if output:
                        existing_ports.append(j)
                        print(existing_ports, "for", switch_v3_name, "already exists in the DB")

            if '-' not in ports[i]:
                new_added_ports.append(ports[i])
                sql = '''select max(id) from cluster.nodeinfo where switch_port is not NULL'''
                cursor.execute(sql)
                temp = cursor.fetchone()
                if temp[0] is None:
                    temp = [0]
                initial_id = temp[0]
                new_added_ports.append(i)

                port = str(ports[i])
                sql = '''select exists(select switch_port from cluster.nodeinfo where switch_port = '{switch_port_key}' and switch_name='{switch_v3_name}')'''.format(
                    switch_port_key=port, switch_v3_name=switch_v3_name)
                cursor.execute(sql)
                output = cursor.fetchone()[0]
                if not output:
                    sql = '''select max(id) from cluster.nodeinfo where switch_port is not NULL'''
                    cursor.execute(sql)
                    temp = cursor.fetchone()
                    if temp[0] is None:
                        temp = [0]
                    initial_id = temp[0]
                    ip_count = int(temp[0]) - int(initial_id)
                    count = '%05d' % (int(temp[0]) + 1)
                    node = node_name + str(count)
                    host_name = node_name + str(count) + "." + domain_name

                    # BMC IP details
                    temp_bmc = switch_based_bmc_details(ip_count)

                    # Admin IP details
                    temp_admin = switch_based_admin_details(temp, initial_id)

                    # IB IP details
                    if ib_status == "True":
                        temp_ib = switch_based_ib_details(temp, initial_id,temp_admin)
                    else:
                        temp_ib = None

                    # Insert details in DB
                    omniadb_connection.insert_switch_based_server(cursor, temp_bmc, temp_admin, temp_ib, node, host_name, switch_v3_ip, switch_v3_name, port, ib_status)

                    if output:
                        existing_ports.append(ports[i])
                        print(existing_ports, "for", switch_v3_name, "already exists in the DB")


insert_switch_details()
