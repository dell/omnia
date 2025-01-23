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
    with open(network_spec_path, "r") as file:
        data = yaml.safe_load(file)
        for info in data["Networks"]:
            for col, value in info.items():
                omnia_nw_names.append(col)


def delete_misc_networks():
    get_networks()
    omnia_networks()
    for i in nw_names:
        if i not in omnia_nw_names:
            command = f"/opt/xcat/bin/rmdef -t network {i}"
            command_list = command.split()
            subprocess.run(command_list, capture_output=True)


delete_misc_networks()
