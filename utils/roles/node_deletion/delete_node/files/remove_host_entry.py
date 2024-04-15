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

#!/usr/bin/env python3

'''
    This module contains tasks required to delete node details from control plane- DB and inventory files
'''

import sys

def remove_all_host(host_list):
    '''
    This module deletes list of host IPs from /etc/hosts
     '''
    # Split the input string by comma and remove any leading/trailing spaces
    ip_list = [ip.strip() for ip in host_list.split(",")]

    # Read the contents of /etc/hosts
    try:
        with open("/etc/hosts","r") as hosts_file:
            hosts_content = hosts_file.readlines()

        with open("/etc/hosts", "w") as hosts_file:
            for line in hosts_content:
                ip_present = False

                for ip in ip_list:
                    if ip in line:
                        ip_present = True
                        break

                if not ip_present:
                    hosts_file.write(line)


    except FileNotFoundError:
        print(file_name + " not found")

    # Print a success message
    print(f"Removed the following IP addresses from /etc/hosts: {', '.join(ip_list)}")

if __name__ == '__main__':
    remove_all_host(sys.argv[1])
