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

import psycopg2 as pg
from cryptography.fernet import Fernet

key_file_path = '/opt/omnia/.postgres/.postgres_pass.key'
pass_file_path = '/opt/omnia/.postgres/.encrypted_pwd'

with open(key_file_path, 'rb') as passfile:
    key = passfile.read()
fernet = Fernet(key)

with open(pass_file_path, 'rb') as datafile:
    encrypted_file_data = datafile.read()
decrypted_pwd = fernet.decrypt(encrypted_file_data).decode()

def create_connection():
    """
    Create a database connection to the omniadb.

    This function establishes a connection to the omniadb database using the provided password.
    It reads the encrypted password from a file, decrypts it using the provided key, and connects to the database.

    Parameters:
        None

    Returns:
        conn (psycopg2.extensions.connection): The database connection.
    """
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
    """
    Create a database connection to the xcatdb.

    This function establishes a connection to the xcatdb database using the provided password.
    It reads the encrypted password from a file, decrypts it using the provided key, and connects to the database.

    Parameters:
        None

    Returns:
        conn (psycopg2.extensions.connection): The database connection.
    """
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
    """
    Inserts node information into the cluster.nodeinfo table.

    Parameters:
        service_tag (str): The service tag of the node.
        node (str): The node name.
        hostname (str): The hostname of the node.
        admin_mac (str): The MAC address of the admin interface.
        admin_ip (Union[str, None]): The IP address of the admin interface.
        bmc_ip (Union[str, None]): The IP address of the BMC.
        discovery_mechanism (str): The mechanism used to discover the node.
        bmc_mode (str): The mode of the BMC.
        switch_ip (Union[str, None]): The IP address of the switch.
        switch_name (str): The name of the switch.
        switch_port (str): The port of the switch.

    Returns:
        None
    """
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
    """
    Inserts switch details into the cluster.switchinfo table.

    Parameters:
        cursor (psycopg2.extensions.cursor): The database cursor.
        switch_name (str): The name of the switch.
        switch_ip (str): The IP address of the switch.

    Returns:
        None
    """
    # Insert switch details to cluster.switchinfo table
    sql = '''INSERT INTO cluster.switchinfo(switch_name,switch_ip) VALUES (%s,%s)'''
    params = (switch_name, switch_ip)
    cursor.execute(sql, params)

    print(f"Inserted switch_ip: {switch_ip} with switch_name: {switch_name} into cluster.switchinfo table")
