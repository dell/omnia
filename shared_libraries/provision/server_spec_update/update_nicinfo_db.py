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
import ipaddress
import uncorrelated_add_ip
import correlation_admin_add_nic
import insert_nicinfo_db
from distutils.util import strtobool
from fetch_booted_node import get_booted_nodes  # Import fetch_booted_nodes

db_path = sys.argv[7]
sys.path.insert(0, db_path)
inventory_status = bool(strtobool(sys.argv[8]))

def validate_input(value):
    """
    Validates the input value.
    Raises:
        ValueError: If the value is empty.
    """
    if value:
        return value

    raise ValueError("Node details cannot be empty")

server_spec_file_path = os.path.abspath(sys.argv[1])
category_nm = sys.argv[2]
metadata_path = os.path.abspath(sys.argv[3])
admin_static_range = sys.argv[4]
admin_nb = sys.argv[5]
node_detail = validate_input(sys.argv[6])

with open(server_spec_file_path, "r") as file:
    data = yaml.safe_load(file)

with open(metadata_path, "r") as file:
    nw_data = yaml.safe_load(file)

# Fetch the list of booted nodes
booted_nic_nodes = get_booted_nodes(db_path)

def generate_ip(nw_name):
    """
    Generates an IP address based on the given network name.

    Args:
        nw_name (str): The name of the network.

    Returns:
        str: The generated IP address.

    Raises:
        ValueError: If the network name is not found in the network data.
        ValueError: If the network mode is not 'static' or 'cidr'.
        ValueError: If the netmask bits are not found in the network data.
        ValueError: If the start or end IP address is not valid.
        ValueError: If the correlation between the network and admin bits is not valid.
        ValueError: If the IP address is not found in the database.
        ValueError: If the IP address is not within the specified range.
        ValueError: If the IP address is already present in the database.
    """
    conn = insert_nicinfo_db.create_connection()
    cursor = conn.cursor()
    net_bits = ""
    for col in nw_data:
        for col_value in nw_data[col]:
            if nw_name in col_value and "netmask_bits" in col_value:
                net_bits = nw_data[col][col_value]
        if col == nw_name:
            nic_range = nw_data[col][0]
            nic_mode = nw_data[col][1]
            if nic_mode == "static":
                nic_ip = uncorrelated_add_ip.cal_uncorrelated_add_ip(cursor, col, nic_mode, nic_range)
                return nic_ip
            if nic_mode == "cidr":
                start_ip = ipaddress.IPv4Address(nic_range.split('-')[0])
                end_ip = ipaddress.IPv4Address(nic_range.split('-')[1])
                output = correlation_admin_add_nic.check_valid_nb(net_bits, admin_nb)
                if output:
                    nic_ip = correlation_admin_add_nic.correlation_admin_to_nic(node_detail, start_ip,
                                                                                net_bits,
                                                                                admin_nb)
                    op = uncorrelated_add_ip.check_presence_ip(cursor, col, nic_ip)
                    if not op and ipaddress.IPv4Address(nic_ip) < end_ip:
                        return nic_ip
                    elif op:
                        nic_ip = uncorrelated_add_ip.cal_uncorrelated_add_ip(cursor, col, nic_mode, nic_range)
                        return nic_ip
                elif not output:
                    nic_ip = uncorrelated_add_ip.cal_uncorrelated_add_ip(cursor, col, nic_mode, nic_range)
                    return nic_ip


# for each node present in a group, it will be called
def update_db_nicinfo():
    """
    Update the nicinfo database with the provided data.

    This function iterates over the 'Categories' in the 'data' dictionary.
    It retrieves the 'category' and 'value' from each 'info' dictionary.
    If the 'category' matches the 'category_nm', it assigns the 'category'
    to 'cat_nm' and populates the 'db_data' dictionary with the 'category'
    and other related information.

    For each 'col' in the 'value' dictionary, it checks if the 'grp_key' is
    'Network' or 'network'. If it is, it iterates over the 'network' in the
    'grp_value' dictionary. It retrieves the 'nicnetwork', 'metric', and
    'nictypes' from each 'net_value' dictionary. It assigns the values to
    'nic_nw', 'nic_nam', 'nic_metric', and 'nic_type' respectively. It also
    checks if 'nicdevices' is present in the 'net_value' dictionary and
    assigns the value to 'nic_device'.

    It then calls the 'generate_ip' function to generate the 'nic_ip' based
    on the 'nic_nw'. It prints the 'nic_nw' and the generated 'nic_ip'.
    It assigns the 'nic_ip' to the 'temp' key in the 'db_data' dictionary.

    Finally, it calls the 'insert_nic_info' function from the 'insert_nicinfo_db'
    module to insert the 'db_data' into the nicinfo database.

    Parameters:
    None

    Returns:
    None
    """
    db_data = {}
    for info in data["Categories"]:
        nic_nw = ""
        for category, value in info.items():
            if category_nm == category:
                cat_nm = category
                db_data['category'] = cat_nm
                for col in value:
                    for grp_key, grp_value in col.items():
#                        for network in grp_value:
                      if grp_key == 'Network' or grp_key == 'network':
                         for network in grp_value:
                            for net_key, net_value in network.items():
                                nic_nw = net_value.get('nicnetwork')
                                nic_nam = net_key
                                nic_metric = net_value.get('metric')
                                db_data[nic_nw] = nic_nam
                                nic_type = net_value.get('nictypes')
                                temp = nic_nw + '_type'
                                db_data[temp] = nic_type
                                temp = nic_nw + "_metric"
                                db_data[temp] = nic_metric
                                temp = nic_nw + '_device'
                                if net_value.get('nicdevices'):
                                    nic_device = net_value.get('nicdevices')
                                    db_data[temp] = nic_device

                            nic_ip = generate_ip(nic_nw)
                            print("IP for", nic_nw, ":", nic_ip)
                            temp = nic_nw + '_ip'
                            db_data[temp] = str(nic_ip)
                insert_nicinfo_db.insert_nic_info(node_detail, db_data)

def main():
    if ((node_detail not in booted_nic_nodes) if inventory_status else (node_detail in booted_nic_nodes)):
        update_db_nicinfo()

if __name__ == "__main__":
    main()
    
