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

import sys
import subprocess

db_path = sys.argv[-1]
sys.path.insert(0, db_path)
import omniadb_connection

# Global variables
switch_name_prefix = "switch"
switch_group = "switch"
switch_snmp_version = 3
switch_auth_type = "sha"

def create_table_switchinfo(conn):
    """
	Create the cluster.switchinfo table in the database.

	Parameters:
	conn (psycopg2.extensions.connection): The database connection.

	Returns:
	None
	"""

    # Create cluster.switchinfo table
    cursor = conn.cursor()
    sql = '''CREATE TABLE IF NOT EXISTS cluster.switchinfo(
        ID SERIAL NOT NULL PRIMARY KEY UNIQUE,
        switch_ip INET,
        switch_name VARCHAR(30))'''
    cursor.execute(sql)
    cursor.close()

def create_switch_object(conn,switch_ip,switch_snmp_username,switch_snmp_password):
    """
	Create switch object for switch_based discovery mechanism by fetching details from cluster.switchinfo table.

	Parameters:
	conn (psycopg2.extensions.connection): The database connection.
	switch_ip (list): A list of switch IPs.
	switch_snmp_username (str): The SNMP username.
	switch_snmp_password (str): The SNMP password.

	Returns:
	None
	"""

    cursor = conn.cursor()
    if switch_ip:
        for ip in switch_ip:
            # Check for existing entries of switch_ip
            sql = f"select exists(select switch_ip from cluster.switchinfo where switch_ip='{ip}')"
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

                omniadb_connection.insert_switch_info(cursor,switch_name,ip)

                # Create switch object
                command = ["/opt/xcat/bin/chdef", switch_name, f"ip={ip}", f"groups={switch_group}"]
                subprocess.run(command)

                # Update xcat switches table with switch credentials
                command = ["/opt/xcat/sbin/tabch", f"switch={switch_name}", f"switches.snmpversion={switch_snmp_version}", f"switches.username={switch_snmp_username}", f"switches.password={switch_snmp_password}", f"switches.auth={switch_auth_type}"]
                subprocess.run(command)

                print(f"Created node object for switch: {switch_name}")
    cursor.close()

def main():
    """
	The main function of the program.

	This function fetches the input arguments from the command line, establishes a connection with the database,
	creates a table in the database if it doesn't exist, and creates switch objects in the database.

	Parameters:
	None

	Returns:
	None
	"""

    # Fetch input arguments
    switch_ip = sys.argv[1:-3]
    switch_snmp_username = sys.argv[-3]
    switch_snmp_password = sys.argv[-2]

    conn = omniadb_connection.create_connection()
    create_table_switchinfo(conn)
    create_switch_object(conn,switch_ip,switch_snmp_username,switch_snmp_password)

    conn.close()

if __name__ == '__main__':
    main()
