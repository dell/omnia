import subprocess
import json
import os
import ipaddress
import sys

def get_network_address(ip_address_netmask):
    """
    Returns the network address of the given IP address and netmask.

    :param ip_address_netmask: A string representing the IP address and netmask in the format "IP/netmask".
    :type ip_address_netmask: str
    :return: A string representing the network address of the given IP address and netmask.
    :rtype: str
    """
    ip_net_address = ipaddress.ip_network(ip_address_netmask, strict=False)
    return str(ip_net_address.network_address)

def main():
    """
    Retrieves the network data from the environment variable 'net_data' and performs network validation.

    Returns:
        str: The IP address of the network.
    """
    network_string = os.environ.get('net_data')
    network_data = json.loads(network_string)
    network_interface = sys.argv[1]
    network_interface_ip = []
    result = subprocess.run(['ip', 'addr', 'show', network_data[network_interface]["nic_name"]], capture_output=True, text=True, check=True)
    for ip in result.stdout.split("inet ")[1:]:
        network_interface_ip.append(ip.split()[0])

    input_network_static_ip_netmask = "{}/{}".format(network_data[network_interface]["static_range"].split("-")[0], network_data[network_interface]["netmask_bits"])
    input_network_dynamic_ip_netmask = "{}/{}".format(network_data[network_interface]["dynamic_range"].split("-")[0], network_data[network_interface]["netmask_bits"])

    for ip in network_interface_ip:
        if ( get_network_address(ip) == get_network_address(input_network_dynamic_ip_netmask)
            or get_network_address(ip) == get_network_address(input_network_static_ip_netmask)):
            print(ip.split("/")[0])

if __name__ == "__main__":
    main()
