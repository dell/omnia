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
import omniadb_connection

# Create a database connection and cursor
conn = omniadb_connection.create_connection()
cursor = conn.cursor()

# Define the current and new node_name values
current_node_name = "control_plane"
new_node_name = "oim"

try:
    # Step 1: Check if the record exists
    select_query = "SELECT * FROM cluster.nodeinfo WHERE node = %s"
    cursor.execute(select_query, (current_node_name,))
    record = cursor.fetchone()
    
    if record:
        print("Record found:", record)
        
        # Step 2: Update the record's node_name
        update_query = "UPDATE cluster.nodeinfo SET node = %s WHERE node = %s"
        cursor.execute(update_query, (new_node_name, current_node_name))
        
        # Save changes to the database
        conn.commit()
        print("Record updated successfully.")
    else:
        print("No record found with node_name =", current_node_name)

except Exception as e:
    # Handle any errors that occur
    print("An error occurred:", e)
    conn.rollback()  # Rollback changes in case of an error

finally:
    # Close the cursor and connection
    cursor.close()
    conn.close()
