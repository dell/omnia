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

#!/usr/bin/python

"""Ansible custom module to set osimage for nodes in a cluster based on discovery mechanism."""

import subprocess
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import omniadb_connection


def validate_osimage(osimage):
    """Validates if the given `osimage` is a string."""
    if not isinstance(osimage, str):
        raise ValueError("osimage must be a string")
    return osimage

def nodeset_mapping_nodes(install_osimage, service_osimage, discovery_mechanism, module):
    """
    Retrieves the nodes from the cluster.nodeinfo table in omniadb and
    then sets the osimage using nodeset command.
    """

    # Establish connection with cluster.nodeinfo
    conn = omniadb_connection.create_connection()
    cursor = conn.cursor()
    sql = "SELECT node, role FROM cluster.nodeinfo WHERE discovery_mechanism = %s"
    cursor.execute(sql, (discovery_mechanism,))
    node_name = cursor.fetchall()
    cursor.close()
    conn.close()

    install_osimage = validate_osimage(install_osimage)
    service_osimage = validate_osimage(service_osimage)

    # Establish connection with omniadb
    conn = omniadb_connection.create_connection_xcatdb()
    cursor = conn.cursor()
    new_mapping_nodes = []
    changed = False

    for node in node_name:
        sql = "SELECT exists(SELECT node FROM nodelist WHERE node = %s AND status IS NULL)"
        cursor.execute(sql, (node[0],))
        output = cursor.fetchone()[0]

        if output:
            if service_osimage != "None" and 'service_node' in node[1]:
                osimage = service_osimage
            else:
                osimage = install_osimage

            new_mapping_nodes.append(node[0])
            command = ["/opt/xcat/sbin/nodeset", node[0], f"osimage={osimage}"]
            try:
                subprocess.run(command, capture_output=True, shell=False, check=True)
                changed = True
            except subprocess.CalledProcessError as e:
                module.warn(f"Failed to execute command '{command}' for node {node[0]}: {e}")

    cursor.close()
    conn.close()

    return {"changed": changed, "nodes_updated": new_mapping_nodes}

def main():
    """
    Main function to handle the nodeset ansible custom module.
    """
    module_args = {
        'discovery_mechanism':{'type':"str", 'required':True},
        'install_osimage':{'type':"str", 'required':True},
        'service_osimage':{'type':"str", 'required':True}
    }

    module = AnsibleModule( argument_spec=module_args, supports_check_mode=True)

    try:
        if module.params["discovery_mechanism"] == "mapping":
            result = nodeset_mapping_nodes(
                module.params["install_osimage"],
                module.params["service_osimage"],
                module.params["discovery_mechanism"],
                module
            )
            module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg=str(e))

if __name__ == "__main__":
    main()
