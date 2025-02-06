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
This script setups the omniadb.

The module creates the omniadb database and cluster.nodeinfo table
"""


import sys

db_path = sys.argv[1]
sys.path.insert(0, db_path)
import omniadb_connection
import psycopg2
from cryptography.fernet import Fernet

key_file_path = '/opt/omnia/.postgres/.postgres_pass.key'
pass_file_path = '/opt/omnia/.postgres/.encrypted_pwd'

def create_db():
    """
    Create a database connection to the PostgreSQL database.

    This function establishes a connection to the PostgreSQL database using the provided password.
    It reads the encrypted password from a file, decrypts it using the provided key, and connects to the database.

    Parameters:
        None

    Returns:
        None
    """

    with open(key_file_path, 'rb') as passfile:
        key = passfile.read()
    fernet = Fernet(key)

    with open(pass_file_path, 'rb') as datafile:
        encrypted_file_data = datafile.read()
    decrypted_pwd = fernet.decrypt(encrypted_file_data).decode()
    conn = None
    try:
        # In PostgreSQL, default username is 'postgres'.
        # And also there is a default database exist named as 'postgres'.
        # Default host is 'localhost' or '127.0.0.1'
        # And default port is '54322'.
        conn = psycopg2.connect("user='postgres' password='" + decrypted_pwd + "' host='localhost' port='5432'")
        print('db connected')

    except Exception as err:
        print("DB not connected")

    if conn is not None:
        conn.autocommit = True

        # Creating cursor object
        cursor = conn.cursor()

        cursor.execute("SELECT datname FROM pg_database;")

        list_database = cursor.fetchall()

        if ("omniadb",) in list_database:
            print("'{}' Database already exists".format("omniadb"))
        else:
            sql = ''' CREATE database omniadb '''
            cursor.execute(sql)
            print("Database created successfully !!")

        conn.close()


def create_db_schema(conn):
    """
    Create a database schema named 'cluster' if it doesn't already exist.

    Parameters:
        conn (psycopg2.extensions.connection): A database connection.

    Returns:
        None
    """
    cursor = conn.cursor()
    sql = ''' CREATE SCHEMA IF NOT EXISTS cluster'''
    cursor.execute(sql)
    cursor.close()


def create_db_table(conn):
    """
    Creates a table named 'nodeinfo' in the 'cluster' schema if it doesn't already exist.
    The table has columns for 'ID', 'service_tag', 'node', 'hostname', 'admin_mac',
    'admin_ip', 'bmc_ip', 'status', 'discovery_mechanism', 'bmc_mode', 'switch_ip',
    'switch_name', 'switch_port', 'cpu', 'gpu', 'cpu_count', and 'gpu_count'.
    The 'ID' column is a serial number, primary key, and unique.
    The function executes the SQL query to create the table and prints a message.
    The function closes the cursor.
    """
    cursor = conn.cursor()

    sql = '''CREATE TABLE IF NOT EXISTS cluster.nodeinfo(
        ID SERIAL NOT NULL PRIMARY KEY UNIQUE,
        service_tag VARCHAR(30),
        node VARCHAR(30),
        hostname VARCHAR(65),
        admin_mac MACADDR,
        admin_ip INET,
        bmc_ip INET,
        status VARCHAR(65),
        discovery_mechanism VARCHAR(65),
        bmc_mode VARCHAR(30),
        switch_ip INET,
        switch_name VARCHAR(30),
        switch_port VARCHAR(10),
        cpu VARCHAR(10),
        gpu VARCHAR(10),
        cpu_count INTEGER,
        gpu_count INTEGER)'''
    cursor.execute(sql)
    print(" DB changes are done")
    cursor.close()

def main():
    """
    Executes the main function of the program.

    This function calls the `create_db` function to create a database connection.
    It then creates a connection to the database using the `create_connection`
    function from the `omniadb_connection` module. After that, it calls the
    `create_db_schema` function to create the database schema and the
    `create_db_table` function to create the database table. Finally, it closes the
    database connection.

    Parameters:
        None

    Returns:
        None
    """
    create_db()
    conn = omniadb_connection.create_connection()
    create_db_schema(conn)
    create_db_table(conn)
    conn.close()

if __name__ == '__main__':
    main()
