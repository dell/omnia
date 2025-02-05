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

#!/usr/bin/env python3.11

'''
    This module contains tasks required to delete node details from Omnia Infrastructure Manager- DB and inventory files
'''

import sys
import subprocess
import os

def delete_node_info_from_oim(nodename):
    """
    Deletes node information from Omnia Infrastructure Manager.

    Parameters:
    - nodename (str): The name of the node to be deleted.

    Returns:
    - None
    """

    try:
        # Delete the entry from /etc/hosts
        command = ['/opt/xcat/sbin/makehosts', '-d', nodename]
        temp = subprocess.run(command, shell=False, check=True)

        # Delete the nodes from xcat
        command = ['/opt/xcat/bin/rmdef', nodename]
        temp = subprocess.run(command, shell=False, check=True)

        # Run DHCP and dns
        command = ['/opt/xcat/sbin/makedhcp', '-a']
        temp = subprocess.run(command, shell=False, check=True)

        command = ['/opt/xcat/sbin/makedhcp', '-n']
        temp = subprocess.run(command, shell=False, check=True)

        command = ['/opt/xcat/sbin/makedns', '-n']
        temp = subprocess.run(command, shell=False, check=True)

    except subprocess.CalledProcessError as e:
        print(f"delete_node_info_from_oim: {e}")



def delete_node_info_from_inventory_files(inv_file_folder, nodeinfo):
    """
    Deletes information from inventory files.

    Parameters:
    - inv_file_folder (str): The path to the folder containing the inventory files.
    - nodeinfo (str): The node information to be deleted.

    Returns:
    - None
    """

    print("Deleting information from inventory files if exists..."+nodeinfo)

    servicetag = ''
    found = False
    inv_files = ["compute_hostname_ip", "compute_gpu_amd", "compute_gpu_nvidia", "compute_cpu_amd", "compute_cpu_intel", "compute_gpu_intel"]
    for file_name in inv_files:
        try:
            file_path = os.path.join(inv_file_folder, file_name)
            with open(file_path, "r") as f:
                new_f = f.readlines()
                print(f"Original contents of {file_name}: {new_f}")

            with open(file_path, "w") as f:
                if new_f:
                    for line in new_f:
                        if nodeinfo.lower() not in line.lower():
                            f.write(line)
                        else:
                            print(f"Deleting line: {line.strip()}")

        except FileNotFoundError:
            print(file_name + " not found")


if __name__ == '__main__':
    delete_node_info_from_oim(sys.argv[1])
    delete_node_info_from_inventory_files(os.path.abspath(sys.argv[2]), sys.argv[1])
