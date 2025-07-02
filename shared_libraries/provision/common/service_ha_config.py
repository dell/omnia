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
"""
This script processes the high availability configuration for service nodes
    and generates a JSON output.
"""
import sys
import json
import os
import traceback
import yaml

if len(sys.argv) != 3:
    print("Usage: python script.py <db_operations_file_path> <high_availability_config_path>")
    sys.exit(1)

db_operations_file_path = sys.argv[1]
ha_config_path = sys.argv[2]

# Add the path to omniadb_connection
sys.path.insert(0, db_operations_file_path)

try:
    import omniadb_connection
except ImportError as e:
    print(f"Failed to import omniadb_connection from {db_operations_file_path}: {e}")
    sys.exit(1)

def get_node_summary(service_tag):
    """Fetch limited node details for a given service tag from the DB."""
    try:
        conn = omniadb_connection.create_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT service_tag, node, hostname, admin_ip FROM cluster.nodeinfo WHERE service_tag = %s",
            (service_tag,)
        )
        records = cursor.fetchall()
        cursor.close()
        conn.close()
        if records:
            node = records[0]
            return {
                "service_tag": node[0],
                "node": node[1],
                "hostname": node[2],
                "admin_ip": node[3]
            }
    except Exception as e:
        print(f"DB query failed for service tag '{service_tag}': {e}")
    return {}

try:
    # Load and validate YAML
    with open(ha_config_path, 'r') as stream:
        data = yaml.safe_load(stream)

    if not data:
        print(f"No content found in {ha_config_path}. Please check the file.")
        sys.exit(1)

    results = {}
    ha = data.get('service_node_ha', {})

    if not isinstance(ha, dict):
        print("Invalid structure for 'service_node_ha'. It must be a dictionary.")
        sys.exit(1)

    if not ha.get('enable_service_ha'):
        print("Service HA is disabled in config. Exiting.")
        sys.exit(0)

    service_nodes = ha.get('service_nodes', [])
    if not service_nodes:
        print("No 'service_nodes' found in service_node_ha. Exiting.")
        sys.exit(1)

    for node in service_nodes:
        vip = node.get('virtual_ip_address', '')
        active_tag = node.get('active_node_service_tag', '')
        passive_nodes_nested = node.get('passive_nodes', [])

        # Active node lookup
        active_info = get_node_summary(active_tag)
        if not active_info:
            print(f"Warning: Active node with service tag '{active_tag}' not found in DB. Skipping this HA config.")
            continue
        active_info.update({
            'virtual_ip': vip,
            'active': True
        })

        # Passive nodes lookup
        passive_info_grouped = []
        for group in passive_nodes_nested:
            tags = group.get('node_service_tags', [])
            if not isinstance(tags, list):
                print(f"Invalid 'node_service_tags' format under VIP '{vip}'; expected a list. Skipping.")
                continue
            for tag in tags:
                passive_info = get_node_summary(tag)
                if passive_info:
                    passive_info.update({
                        'virtual_ip': vip,
                        'active': False
                    })
                    passive_info_grouped.append(passive_info)

        # Assemble node data
        node_key = active_info['service_tag']
        node_data = [active_info] + passive_info_grouped
        results[node_key] = node_data

    if not results:
        print("No valid service HA data found. Exiting without writing output.")
        sys.exit(1)

    # Write JSON output
    OUTPUT_DIR = "/opt/omnia/service_nodes/"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file_path = os.path.join(OUTPUT_DIR, 'service_ha_config_data.json')
    with open(output_file_path, 'w') as outfile:
        json.dump(results, outfile, indent=4)

    print(f"Service HA config written to: {output_file_path}")

except yaml.YAMLError as e:
    print("YAML error:", e)
    sys.exit(1)
except Exception as e:
    print("An unexpected error occurred:")
    traceback.print_exc()
    sys.exit(1)
