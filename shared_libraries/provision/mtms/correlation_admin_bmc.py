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

import ipaddress
import calculate_ip_details


def correlation_bmc_to_admin(bmc_ip, admin_ip_subnet, netmask_bits):
    """
    Calculates the correlated admin ip based on the given bmc_ip, admin_ip_subnet, and netmask_bits.

    Parameters:
    - bmc_ip (str): The bmc ip that needs to be used to form the correlated admin ip.
    - admin_ip_subnet (str): The network bits to be used for the correlated admin ip.
    - netmask_bits (int): The netmask bits of the admin and bmc ip.

    Returns:
    - final_admin_ip (ipaddress.IPv4Address): The correlated admin ip.
    """

    binary_admin_ip = calculate_ip_details.calculate_binary_ip(admin_ip_subnet)
    binary_bmc_ip = calculate_ip_details.calculate_binary_ip(bmc_ip)
    first_x_bits = calculate_ip_details.calculate_first_x_bits(binary_admin_ip, netmask_bits)
    last_y_bits = calculate_ip_details.calculate_last_y_bits(binary_bmc_ip, netmask_bits)
    final_admin_ip_binary = first_x_bits + last_y_bits
    int_final_admin_ip = int(final_admin_ip_binary, 2)
    final_admin_ip = ipaddress.IPv4Address(int_final_admin_ip)
    return final_admin_ip