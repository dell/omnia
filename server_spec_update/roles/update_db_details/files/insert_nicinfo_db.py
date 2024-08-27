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


def create_connection():
    with open('/opt/omnia/.postgres/.postgres_pass.key', 'rb') as passfile:
        key = passfile.read()
    fernet = Fernet(key)

    with open('/opt/omnia/.postgres/.encrypted_pwd', 'rb') as datafile:
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

    query = f'''SELECT EXISTS(SELECT id FROM cluster.nicinfo WHERE id='{id}')'''
    cursor.execute(query)
    output = cursor.fetchone()[0]
    return output


def insert_nic_info(ip, db_data):
    conn = create_connection()
    cursor = conn.cursor()
    sql_query = f"SELECT id FROM cluster.nodeinfo where admin_ip='{ip}'"
    cursor.execute(sql_query)
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
            query = f"UPDATE cluster.nicinfo SET {set_clause} WHERE id = {id_no[0]}"
            try:
                print("DB data=", db_data)
                cursor.execute(query, db_data)
            except Exception as e:
                print(e)

    else:
        print(ip, " Not present in the DB. Please provide proper IP")

    cursor.close()
    conn.close()
