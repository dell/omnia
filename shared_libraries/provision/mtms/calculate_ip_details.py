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


def convert_binary_decimal(binary_mask):
    """
    Converts a binary netmask to a decimal netmask.

    Parameters:
      binary_mask (str): The binary netmask to convert.

    Returns:
      str: The decimal netmask.
    """

    netmask = ipaddress.IPv4Address(int(binary_mask, 2)).exploded
    return netmask


def calculate_binary_mask(prefix_length):
    """
    Calculates the binary netmask based on the given prefix length.

    Parameters:
    - prefix_length (int): The prefix length of the netmask.

    Returns:
    - str: The binary netmask.
    """

    binary_mask = '1' * int(prefix_length) + '0' * (32 - int(prefix_length))
    return binary_mask


def calculate_first_x_bits(ip_binary, netmask_bits):
    """
    Calculates the first x bits of a given IP binary. i.e. the network bits for correlation

    Parameters:
    - ip_binary (str): The IP binary.
    - netmask_bits (int): The number of netmask bits.

    Returns:
    - str: The first x bits of the IP binary.
    """

    x = int(netmask_bits)
    ip_x_binary = ip_binary[:x]
    return ip_x_binary


def calculate_last_y_bits(ip_binary, netmask_bits):
    """
    Calculates the last y bits of a given IP binary. i.e. the host bits for correlation

    Parameters:
    - ip_binary (str): The IP binary.
    - netmask_bits (int): The number of netmask bits.

    Returns:
    - str: The last y bits of the IP binary.
    """

    y = 32 - int(netmask_bits)
    ip_y_binary = ip_binary[-y:]
    return ip_y_binary


def calculate_binary_ip(ip):
    """
    Calculates the binary representation of a given IP address.

    Parameters:
    - ip (str): The IP address to calculate the binary representation for.

    Returns:
    - str: The binary representation of the IP address.
    - str: "Invalid IP address" if the IP address is not valid.
    """

    try:
        octets = map(int, ip.split('.'))
        if octets:
          binary = ''.join(f'{octet:08b}' for octet in octets)
          return binary

    except ValueError:
        return "Invalid IP address"


def cal_ip_details(temp, netmask_bits):
    """
    Calculates the network details for a given IP address and netmask.

    Parameters:
    - temp (str): The IP address.
    - netmask_bits (int): The number of netmask bits.

    Returns:
    - tuple: A tuple containing the netmask and the network address.
    """

    binary_mask = calculate_binary_mask(netmask_bits)
    netmask = convert_binary_decimal(binary_mask)
    subnet = ipaddress.IPv4Network(f'{temp}/{netmask}', strict=False)
    return netmask, subnet.network_address


def create_cidr_range(cidr):
    """
    Creates a CIDR range from the given CIDR string.

    Args:
        cidr (str): The CIDR string.

    Returns:
        Tuple[str, str]: A tuple containing the start IP and end IP of the CIDR range.
    """
    ip_range = [str(ip) for ip in ipaddress.IPv4Network(cidr)]
    size = len(ip_range)
    start_ip = ip_range[1]
    end_ip = ip_range[size - 2]
    return start_ip, end_ip
