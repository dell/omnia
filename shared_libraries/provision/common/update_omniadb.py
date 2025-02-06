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

db_path = os.path.abspath(sys.argv[1])
node = sys.argv[2]

sys.path.insert(0, db_path)
import omniadb_connection

def update_node_status(node):
    """
	Updates the status of a node in the cluster.nodeinfo table in omniadb.

	Parameters:
	    node (str): The name of the node to update.

	Returns:
	    None
	"""

    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()

    update_status_query = """
        UPDATE cluster.nodeinfo
        SET status = 'booted'
        WHERE node = %s
    """
    cursor.execute(update_status_query, (node,))
    cursor.close()
    conn.close()

update_node_status(node)