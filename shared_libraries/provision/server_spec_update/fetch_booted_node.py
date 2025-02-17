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

import sys
import os
import yaml
import ipaddress
import uncorrelated_add_ip
import correlation_admin_add_nic

def get_booted_nodes(db_path):
    print(f"Debug: In get_booted_nodes with db_path: {db_path}")
 
    # Insert db_path at the start of sys.path
    if db_path not in sys.path:
        sys.path.insert(0, db_path)
 
    try:
        import omniadb_connection
    except ImportError as e:
        print(f"Error importing omniadb_connection: {e}")
        return []
 
    # Establish a connection with omniadb
    try:
        conn = omniadb_connection.create_connection()
        cursor = conn.cursor()
    except Exception as e:
        print(f"Error establishing connection: {e}")
        return []
 
    try:
        # Execute the SQL query to fetch booted nodes
        sql_query = "SELECT admin_ip FROM cluster.nodeinfo WHERE status = 'booted'"
        cursor.execute(sql_query)
 
        # Fetch all rows from the result set
        rows = cursor.fetchall()
 
        # Extract the node names
        booted_nodes = [row[0] for row in rows]
 
        return booted_nodes
 
    except Exception as e:
        print(f"Error fetching booted nodes: {e}")
        return []
 
    finally:
        # Close the cursor and connection
        cursor.close()
        conn.close()
