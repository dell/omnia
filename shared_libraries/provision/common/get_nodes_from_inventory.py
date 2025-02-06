# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os
import subprocess
import re

# Paths to the inventory file and database module
inventory_file_paths = sys.argv[2][1:-1].split(',')  # Extract the inventory file path correctly
db_path = os.path.abspath(sys.argv[1])

sys.path.insert(0, db_path)
import omniadb_connection

# Read the inventory file line-by-line, ignoring sections like [nodes]
node_identifiers = []
if inventory_file_paths:
    for inventory_file_path in inventory_file_paths:
        inventory_file_path = os.path.abspath(inventory_file_path.strip("'| "))
        with open(os.path.abspath(inventory_file_path), "r") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("["):
                    node_identifiers.append(line)

def is_ip(identifier):
    """
	Check if the given identifier is a valid IP address.

	Parameters:
		identifier (str): The identifier to check.

	Returns:
		bool: True if the identifier is a valid IP address, False otherwise.
    """

    return re.match(r"^\d{1,3}(\.\d{1,3}){3}$", identifier) is not None

def fetch_node_name(cursor, identifier):
    """
    Fetches the node name from the database based on the given identifier.

    Parameters:
        cursor (psycopg2.extensions.cursor): The database cursor object.
        identifier (str): The identifier to search for.

    Returns:
        str or None: The node name if found, None otherwise.
    """
    if is_ip(identifier):
        cursor.execute(sql_query, (identifier,))
    else:
        identifier = identifier.split('ansible_host=')[1]
        cursor.execute(sql_query, (identifier,))

    node_row = cursor.fetchone()

    return node_row[0] if node_row and node_row[1] == 'failed' else None

def get_nodes_name():
    """
	Retrieves the names of the nodes from the database based on the given identifiers.

	Parameters:
		None

	Returns:
		list: A list of strings representing the names of the nodes.
	"""

    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    node_names = []
    for identifier in node_identifiers:
        # Try to fetch the node name based on the identifier
        node_name = fetch_node_name(cursor, identifier)
        if node_name:
            node_names.append(node_name.strip())

    # Close the cursor and connection
    cursor.close()
    conn.close()
    return node_names

node_names = get_nodes_name()
print(','.join(set(node_names)))