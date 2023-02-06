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
import psycopg2
import warnings
import re

static_stanza_path = sys.argv[1]
serial = []
bmc = []
node_name = sys.argv[2]
bmc_mode = "static"
domain_name = sys.argv[3]
pxe_subnet = sys.argv[4]
ib_status = sys.argv[5]
ib_subnet = sys.argv[6]


def extract_serial_bmc():
    # Extract the bmc IP and serial of the nodes from the stanza file
    file = open(static_stanza_path)
    for line in file:
        temp = ""
        if 'serial=' in line:
            temp = line.split("=")[-1].strip()
            serial.append(temp)
        if 'bmc=' in line:
            bmc.append(line.split("=")[-1].strip())
    file.close()
    update_db()


def update_stanza_file(service_tag, nodename):
    # Update the node object name in static stanzas file
    with open(static_stanza_path, "r+") as file:
        data = file.read()
        rep_text = re.sub(f'node-.*-{service_tag}:', f'{nodename}' + ':', data)
        file.seek(0)
        file.truncate()
        file.write(rep_text)
        file.close()


def update_db():
    # Establish a connection with omniadb
    conn = psycopg2.connect(
        database="omniadb",
        user='postgres',
        host='localhost',
        port='5432')
    conn.autocommit = True
    cursor = conn.cursor()

    for key in range(0, len(serial)):
        sql = '''select exists(select serial,bmc_ip from cluster.nodeinfo where bmc_ip='{key}' and serial='{serial_key}')'''.format(
            key=bmc[key], serial_key=serial[key])
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
            admin_ip = pxe_subnet.split('.')[0] + "." + pxe_subnet.split('.')[1] + "." + bmc[key].split('.')[2] + "." + \
                       bmc[key].split('.')[3]
            sql = '''select exists(select admin_ip from cluster.nodeinfo where admin_ip='{key}')'''.format(key=admin_ip)
            cursor.execute(sql)

            update_stanza_file(serial[key].lower(), node)

            admin_output = cursor.fetchone()[0]
            if admin_output == False and ib_status == "False":
                sql = '''INSERT INTO cluster.nodeinfo(serial,node,hostname,admin_ip,bmc_ip,bmc_mode) VALUES (
                    '{serial_key}','{node_name}','{host_name}','{admin_ip}','{bmc_ip}','{bmc_mode}')'''.format(
                    serial_key=serial[key], node_name=node, host_name=host_name, admin_ip=admin_ip, bmc_ip=bmc[key],
                    bmc_mode=bmc_mode)
                cursor.execute(sql)

            if admin_output == False and ib_status == "True":
                ib_ip = ib_subnet.split('.')[0] + "." + ib_subnet.split('.')[1] + "." + bmc[key].split('.')[
                    2] + "." + bmc[key].split('.')[3]
                sql = '''INSERT INTO cluster.nodeinfo(serial,node,hostname,admin_ip,ib_ip,bmc_ip,bmc_mode) VALUES (
                    '{serial_key}','{node_name}','{host_name}','{admin_ip}','{ib_ip}','{bmc_ip}','{bmc_mode}')'''.format(
                    serial_key=serial[key], node_name=node, host_name=host_name, admin_ip=admin_ip, ib_ip=ib_ip,
                    bmc_ip=bmc[key],
                    bmc_mode=bmc_mode)
                cursor.execute(sql)

            if admin_output:
                warnings.warn('Admin IP already present in the database')
                print(admin_ip)
        else:
            warnings.warn('Node already present in the database')
            print(serial[key])
    cursor.close()
    conn.close()


extract_serial_bmc()
