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

import sys, os
import yaml
import subprocess

db_path = sys.argv[1]
sys.path.insert(0, db_path)
import omniadb_connection

network_spec_path = os.path.abspath(sys.argv[2])
nw_names = []
omnia_nw_names = []


def get_networks():
    """
    Retrieves the list of network names from the `networks` table in the `xcatdb` database.

    This function establishes a connection with the `xcatdb` database and executes a SQL query to
    retrieve the `netname` column from the `networks` table. The retrieved values are stored in the
    `nw_names` list.

    Parameters:
        None

    Returns:
        None
    """
    conn_x = omniadb_connection.create_connection_xcatdb()
    cursor_x = conn_x.cursor()
    sql = "SELECT netname FROM networks"
    cursor_x.execute(sql)
    temp = cursor_x.fetchall()
    for nw in temp:
        nw_names.append(nw[0])
    cursor_x.close()
    conn_x.close()


def omnia_networks():
    """
    Extracts network names from a YAML file and appends them to a list.

    This function opens a file specified by the `network_spec_path` variable and reads its contents.
    The contents are parsed as a YAML file and stored in the `data` variable.
    The function then iterates over the `Networks` key in the `data` dictionary.
    For each item in the `Networks` list, it iterates over the key-value pairs in the item.
    The keys are appended to the `omnia_nw_names` list.

    Parameters:
        None

    Returns:
        None
    """
    with open(network_spec_path, "r") as file:
        data = yaml.safe_load(file)
        for info in data["Networks"]:
            for col, value in info.items():
                omnia_nw_names.append(col)


def delete_misc_networks():
    """
    Deletes miscellaneous networks from the system.

    This function retrieves the names of all the networks in the system using the `get_networks()` function.
    It then retrieves the names of the networks specific to Omnia using the `omnia_networks()` function.
    The function then iterates over the names of all the networks and checks if they are not present in the
    list of Omnia-specific network names. If a network name is not present in the list of Omnia-specific
    network names, it constructs a command to delete the network using the `rmdef` utility. The command is
    executed using the `subprocess.run()` function.

    Parameters:
        None

    Returns:
        None
    """
    get_networks()
    omnia_networks()
    for i in nw_names:
        if i not in omnia_nw_names:
            command = f"/opt/xcat/bin/rmdef -t network {i}"
            command_list = command.split()
            subprocess.run(command_list, capture_output=True)


delete_misc_networks()
