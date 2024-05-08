# Copyright 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
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
from cryptography.fernet import Fernet

with open('/opt/omnia/.postgres/.postgres_pass.key', 'rb') as passfile:
    key = passfile.read()
fernet = Fernet(key)

with open('/opt/omnia/.postgres/.encrypted_pwd', 'rb') as datafile:
    encrypted_file_data = datafile.read()
decrypted_pwd = fernet.decrypt(encrypted_file_data).decode()

def create_connection():
    # Create database connection
    conn = pg.connect(
        database="omniadb",
        user="postgres",
        password=decrypted_pwd,
        host="localhost",
        port="5432",
    )
    conn.autocommit = True
    return conn


def create_connection_xcatdb():
    # Create database connection
    conn = pg.connect(
        database="xcatdb",
        user="postgres",
        password=decrypted_pwd,
        host="localhost",
        port="5432",
    )
    conn.autocommit = True
    return conn


def insert_node_info(service_tag, node, hostname, admin_mac, admin_ip, bmc_ip, discovery_mechanism, bmc_mode, switch_ip,
                     switch_name, switch_port):
    conn = create_connection()
    cursor = conn.cursor()
    sql = '''INSERT INTO cluster.nodeinfo(service_tag,node,hostname,admin_mac,admin_ip,bmc_ip,discovery_mechanism,bmc_mode,switch_ip,switch_name,switch_port)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
    params = (
        service_tag, node, hostname, admin_mac, str(admin_ip) if admin_ip else None, str(bmc_ip) if bmc_ip else None,
        discovery_mechanism, bmc_mode, str(switch_ip) if switch_ip else None, switch_name, switch_port)
    cursor.execute(sql, params)
    conn.close()

def insert_switch_info(cursor, switch_name, switch_ip):
    # Insert switch details to cluster.switchinfo table
    sql = '''INSERT INTO cluster.switchinfo(switch_name,switch_ip) VALUES (%s,%s)'''
    params = (switch_name, switch_ip)
    cursor.execute(sql, params)

    print(f"Inserted switch_ip: {switch_ip} with switch_name: {switch_name} into cluster.switchinfo table")
