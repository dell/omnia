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
import psycopg2

def create_db():
    conn = None
    try:
        # In PostgreSQL, default username is 'postgres'.
        # And also there is a default database exist named as 'postgres'.
        # Default host is 'localhost' or '127.0.0.1'
        # And default port is '54322'.
        conn = psycopg2.connect("user='postgres' host='localhost'  port='5432'")
        print('db connected')

    except:
        print('Database not connected.')

    if conn is not None:
        conn.autocommit = True

        # Creating cursor object
        cursor = conn.cursor()

        cursor.execute("SELECT datname FROM pg_database;")

        list_database = cursor.fetchall()

        if ("omniadb",) in list_database:
            print("'{}' Database already exists".format("omniadb"))
        else:
            sql = ''' CREATE database omniadb ''';
            cursor.execute(sql)
            print("Database created successfully !!");

        conn.close()

def create_db_schema(conn):

    cursor = conn.cursor()
    sql = ''' CREATE SCHEMA IF NOT EXISTS cluster'''
    cursor.execute(sql)
    cursor.close()

def create_db_table(conn):

    cursor = conn.cursor()

    sql = '''CREATE TABLE IF NOT EXISTS cluster.nodeinfo(
        ID SERIAL NOT NULL PRIMARY KEY UNIQUE,
        serial VARCHAR(30),
        node VARCHAR(30),
        hostname VARCHAR(65),
        admin_mac MACADDR,
        admin_ip INET,
        bmc_ip INET,
        ib_ip INET,
        status VARCHAR(65),
        bmc_mode VARCHAR(30),
        switch_ip INET,
        switch_name VARCHAR(30),
        switch_port VARCHAR(10))'''
    cursor.execute(sql)
    print(" DB changes are done")
    cursor.close()

def main():

   create_db()
   conn = omniadb_connection.create_connection()
   create_db_schema(conn)
   create_db_table(conn)
   conn.close()

if __name__ == '__main__':
    main()
