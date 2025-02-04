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

import ipaddress
import sys

cal_path = "/opt/omnia/shared_libraries/provision/mtms"
sys.path.insert(0, cal_path)
import calculate_ip_details


def check_valid_nb(nic_nb, admin_nb):

    if int(admin_nb) <= int(nic_nb):
        return True
    else:
        return False


def correlation_admin_to_nic(admin_ip, nic_ip, nic_nb, admin_nb):
    """
       Calculates the correlated admin ip
       Parameters:
         admin_ip: ip that needs to be used to form correlated admin ip
         nic_ip: admin range to be used for correlated admin ip
         nic_nb: netmask bits of nic that needs correlation
         admin_nb: netmask bits of admin
       Returns:
         correlated admin ip
    """

    binary_admin_ip = calculate_ip_details.calculate_binary_ip(str(admin_ip))
    binary_nic_ip = calculate_ip_details.calculate_binary_ip(str(nic_ip))
    first_x_bits = calculate_ip_details.calculate_first_x_bits(binary_nic_ip, nic_nb)
    last_y_bits = calculate_ip_details.calculate_last_y_bits(binary_admin_ip, nic_nb)
    final_ip_binary = first_x_bits + last_y_bits
    int_final_ip = int(final_ip_binary, 2)
    final_ip = ipaddress.IPv4Address(int_final_ip)
    return final_ip
