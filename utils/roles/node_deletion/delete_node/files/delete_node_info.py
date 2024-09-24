# Copyright 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
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
    This module contains tasks required to delete node details from control plane- DB and inventory files
'''

import sys
import subprocess


def delete_node_info_from_cp(nodename):
    '''
    This modules deletes node object 
    '''
    
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
        print(f"delete_node_info_from_cp: {e}")

    

def delete_node_info_from_inventory_files(inv_file_folder, nodeinfo):
    '''
    This module deletes node information from invenotry files
    '''
    print("Deleting information from inventory files if exists..."+nodeinfo)

    servicetag = ''
    found = False
    inv_files = ["compute_servicetag_ip", "compute_gpu_amd", "compute_gpu_nvidia", "compute_cpu_amd", "compute_cpu_intel"]
    for file_name in inv_files: 
        try:
            with open(inv_file_folder+file_name,"r") as f:
                new_f = f.readlines()
            
            with open(inv_file_folder+file_name, "w") as f:
                for line in new_f:
                    if nodeinfo.lower() not in line:
                        f.write(line)
            
        except FileNotFoundError:
            print(file_name + " not found")


if __name__ == '__main__':
    delete_node_info_from_cp(sys.argv[1])
    delete_node_info_from_inventory_files(sys.argv[2], sys.argv[3])
