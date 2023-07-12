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

import psycopg2 as pg


def create_connection():
    # Create database connection
    conn = pg.connect(
        database="omniadb",
        user="postgres",
        host="localhost",
        port="5432",
    )
    conn.autocommit = True
    return conn


def insert_switch(cursor, switch_name, switch_ip):
    # Insert switch details to cluster.switchinfo table
    sql = '''INSERT INTO cluster.switchinfo(switch_name,switch_ip) VALUES ('{switch_name}','{switch_ip}')'''.format(
        switch_name=switch_name, switch_ip=switch_ip)
    cursor.execute(sql)

    print(f"Inserted switch_ip: {switch_ip} with switch_name: {switch_name} into cluster.switchinfo table")


def insert_switch_based_server(cursor, bmc_ip, admin_ip, ib_ip, node, hostname, switch_ip, switch_name, switch_port,
                               ib_status):
    if ib_status == "False":
        sql = '''INSERT INTO cluster.nodeinfo(bmc_ip, admin_ip, ib_ip, node, hostname, switch_ip, switch_name, switch_port) VALUES ('{bmc_ip}','{admin_ip}',NULL, '{node}', '{hostname}' ,'{switch_ip}' ,'{switch_name}', '{switch_port}')'''.format(
            bmc_ip=bmc_ip, admin_ip=admin_ip, node=node, hostname=hostname, switch_ip=switch_ip,
            switch_name=switch_name,
            switch_port=switch_port)
        cursor.execute(sql)
    elif ib_status == "True":
        sql = '''INSERT INTO cluster.nodeinfo(bmc_ip, admin_ip, ib_ip, node, hostname, switch_ip, switch_name, switch_port) VALUES ('{bmc_ip}','{admin_ip}','{ib_ip}', '{node}', '{hostname}' , '{switch_ip}', '{switch_name}', '{switch_port}')'''.format(
            bmc_ip=bmc_ip, admin_ip=admin_ip, ib_ip=ib_ip, node=node, hostname=hostname, switch_ip=switch_ip,
            switch_name=switch_name, switch_port=switch_port)
        cursor.execute(sql)


def insert_cp_details_db(cursor, node_name, network_interface_type, bmc_nic_ip, admin_nic_ip, pxe_mac_address, hostname):

    if network_interface_type == "lom":
        sql = '''INSERT INTO cluster.nodeinfo(node, bmc_ip, admin_ip, admin_mac, hostname) VALUES ('{node}','{bmc_ip}','{admin_ip}', '{admin_mac}', '{hostname}')'''.format(
            node=node_name, bmc_ip=bmc_nic_ip, admin_ip=admin_nic_ip, admin_mac=pxe_mac_address, hostname=hostname)
        cursor.execute(sql)

    if network_interface_type == "dedicated":
        sql = '''INSERT INTO cluster.nodeinfo(node, admin_ip, admin_mac, hostname) VALUES ('{node}','{admin_ip}','{admin_mac}', '{hostname}')'''.format(
             node=node_name, admin_ip=admin_nic_ip, admin_mac=pxe_mac_address, hostname=hostname)
        cursor.execute(sql)
    cursor.close()
