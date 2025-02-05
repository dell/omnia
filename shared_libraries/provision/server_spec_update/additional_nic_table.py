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

import yaml
import sys, os

node_db_path = sys.argv[2]
sys.path.insert(0, node_db_path)
import omniadb_connection

network_spec_file_path = os.path.abspath(sys.argv[1])
with open(network_spec_file_path, "r") as file:
    data = yaml.safe_load(file)


def create_nicinfo_table():
    """
	Create the 'nicinfo' table in the 'cluster' schema if it doesn't already exist.

	The table has columns for various network related information such as IP addresses, types, and metrics.
	It also has a foreign key constraint to the 'nodeinfo' table in the 'cluster' schema.

	The function also dynamically adds columns to the 'nicinfo' table based on the data in the 'Networks' list.
	If the 'VLAN' key is present in the data, it also adds columns for the VLAN information.

	Finally, it commits the changes to the database and prints a success message.

	Parameters:
	None

	Returns:
	None
	"""

    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = '''CREATE TABLE IF NOT EXISTS cluster.nicinfo(
           ID SERIAL NOT NULL PRIMARY KEY UNIQUE,
           category VARCHAR(60),
           FOREIGN KEY (id)
           REFERENCES cluster.nodeinfo(id)
           ON DELETE CASCADE)'''
    cursor.execute(sql)

    for info in data["Networks"]:
        for col, value in info.items():
            if col not in ('admin_network', 'bmc_network'):
                if value.get('VLAN'):
                    col_sql = f"ALTER TABLE cluster.nicinfo ADD COLUMN IF NOT EXISTS {col} VARCHAR(60), ADD COLUMN IF NOT EXISTS {col}_ip INET, " \
                              f"ADD COLUMN IF NOT EXISTS {col}_type VARCHAR(30), ADD COLUMN IF NOT EXISTS {col}_metric VARCHAR(10), " \
                              f"ADD COLUMN IF NOT EXISTS {col}_device VARCHAR(30)"
                    cursor.execute(col_sql)
                else:
                    col_sql = f"ALTER TABLE cluster.nicinfo ADD COLUMN IF NOT EXISTS {col} VARCHAR(60), ADD COLUMN IF NOT EXISTS {col}_ip INET, " \
                              f"ADD COLUMN IF NOT EXISTS {col}_type VARCHAR(30), ADD COLUMN IF NOT EXISTS {col}_metric VARCHAR(10)"
                    cursor.execute(col_sql)

    conn.commit()
    print(" DB changes are done")
    cursor.close()


create_nicinfo_table()
