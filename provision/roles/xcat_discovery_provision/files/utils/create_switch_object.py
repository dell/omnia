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
import sys
import subprocess

# Global variables
switch_name_prefix = "switch"
switch_group = "switch"
switch_snmp_version = 3
switch_auth_type = "sha"

def create_table_switchinfo(conn):

    # Create cluster.switchinfo table
    cursor = conn.cursor()
    sql = '''CREATE TABLE IF NOT EXISTS cluster.switchinfo(
        ID SERIAL NOT NULL PRIMARY KEY UNIQUE,
        switch_ip INET,
        switch_name VARCHAR(30))'''
    cursor.execute(sql)
    cursor.close()

def create_switch_object(conn,switch_ip,switch_snmp_username,switch_snmp_password):

    cursor = conn.cursor()
    for ip in switch_ip:
        # Check for existing entries of switch_ip
        sql = '''select exists(select switch_ip from cluster.switchinfo where switch_ip='{ip}')'''.format(ip=ip)
        cursor.execute(sql)
        output_switch_ip = cursor.fetchone()[0]

        if not output_switch_ip:
            # Generate switch_name
            sql = '''select id from cluster.switchinfo ORDER BY id DESC LIMIT 1'''
            cursor.execute(sql)
            id_number = cursor.fetchone()
            if id_number is None:
                id_number = [0]
            switch_id = int(id_number[0]) + 1
            switch_name = switch_name_prefix + str(switch_id)

            omniadb_connection.insert_switch(cursor,switch_name,ip)

            # Create switch object
            command = f"chdef {switch_name} ip={ip} groups={switch_group}"
            create_switch_object = subprocess.run([f'{command}'], shell=True)

            # Update xcat switches table with switch credentials
            command = f"tabch switch={switch_name} switches.snmpversion={switch_snmp_version} switches.username={switch_snmp_username} switches.password={switch_snmp_password} switches.auth={switch_auth_type}"
            update_table_switches = subprocess.run([f'{command}'], shell=True)

            print(f"Created node object for switch: {switch_name}")
    cursor.close()

def main():
   
   # Fetch input arguments
   switch_ip = sys.argv[1:-2]
   switch_snmp_username = sys.argv[-2]
   switch_snmp_password = sys.argv[-1]

   conn = omniadb_connection.create_connection()
   create_table_switchinfo(conn)
   create_switch_object(conn,switch_ip,switch_snmp_username,switch_snmp_password)

   conn.close()

if __name__ == '__main__':
    main()
