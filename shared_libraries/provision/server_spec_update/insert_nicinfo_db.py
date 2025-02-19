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

"""
This module contains functions for inserting NIC information into a database.
"""

key_file_path = '/opt/omnia/.postgres/.postgres_pass.key'
pass_file_path = '/opt/omnia/.postgres/.encrypted_pwd'

def create_connection():
    """
    Create a database connection using the provided password file.

    This function reads the encrypted password from a file and decrypts it using the provided key.
    It then establishes a connection to the PostgreSQL database using the decrypted password.

    Returns:
        conn (psycopg2.extensions.connection): The database connection object.

    Raises:
        FileNotFoundError: If the password file or key file is not found.
        PermissionError: If the password file or key file cannot be read.
        cryptography.fernet.InvalidToken: If the decryption of the password fails.
        psycopg2.OperationalError: If the database connection fails.

    """
    with open(key_file_path, 'rb') as passfile:
        key = passfile.read()
    fernet = Fernet(key)

    with open(pass_file_path, 'rb') as datafile:
        encrypted_file_data = datafile.read()
    decrypted_pwd = fernet.decrypt(encrypted_file_data).decode()
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


def check_presence_id(cursor, id):
    """
        Check presence of bmc ip in DB.
        Parameters:
            cursor: Pointer to omniadb DB.
            id: id whose presence we need to check in DB.
        Returns:
            bool: that gives true or false if the bmc ip is present in DB.
    """

    query = f'''SELECT EXISTS(SELECT id FROM cluster.nicinfo WHERE id=%s)'''
    cursor.execute(query, (id,))
    output = cursor.fetchone()[0]
    return output


def insert_nic_info(ip, db_data):
    """
    Inserts or updates NIC information in the database.

    Args:
        ip (str): The IP address of the node.
        db_data (dict): A dictionary containing the NIC information to be inserted or updated.

    Returns:
        None

    Raises:
        Exception: If there is an error executing the SQL query.

    """
    conn = create_connection()
    cursor = conn.cursor()
    sql_query = "SELECT id FROM cluster.nodeinfo where admin_ip=%s"
    cursor.execute(sql_query, (ip,))
    id_no = cursor.fetchone()
    if id_no is not None:
        op = check_presence_id(cursor, id_no[0])
        if not op:
            db_data['id'] = id_no[0]
            columns = ', '.join(db_data.keys())
            placeholders = ', '.join(f'%({col})s' for col in db_data.keys())
            query = f"INSERT INTO cluster.nicinfo ({columns}) VALUES ({placeholders})"
            try:
                print("DB data=", db_data)
                cursor.execute(query, db_data)
            except Exception as e:
                print(e)
        elif op:
            set_clause = ', '.join(f'{col} = COALESCE({col}, %({col})s)' if col != 'category' and col.endswith(
                'ip') else f'{col} = %({col})s' for col in db_data.keys())
            query = f"UPDATE cluster.nicinfo SET {set_clause} WHERE id=%(id)s"

            try:
                print("DB data=", db_data)
                cursor.execute(query, {**db_data, 'id': id_no[0]})
            except Exception as e:
                print(e)

    else:
        print(ip, " Not present in the DB. Please provide proper IP")

    cursor.close()
    conn.close()
    
