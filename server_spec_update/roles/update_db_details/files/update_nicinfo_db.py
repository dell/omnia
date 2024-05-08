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

import sys
import yaml
import ipaddress
import uncorrelated_add_ip
import correlation_admin_add_nic
import insert_nicinfo_db

server_spec_file_path = sys.argv[1]
category_nm = sys.argv[2]
metadata_path = sys.argv[3]
admin_static_range = sys.argv[4]
admin_nb = sys.argv[5]
node_detail = sys.argv[6]

with open(server_spec_file_path, "r") as file:
    data = yaml.safe_load(file)

with open(metadata_path, "r") as file:
    nw_data = yaml.safe_load(file)


def generate_ip(nw_name):
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
                    if not op and nic_ip < end_ip:
                        return nic_ip
                    elif op:
                        nic_ip = uncorrelated_add_ip.cal_uncorrelated_add_ip(cursor, col, nic_mode, nic_range)
                        return nic_ip
                elif not output:
                    nic_ip = uncorrelated_add_ip.cal_uncorrelated_add_ip(cursor, col, nic_mode, nic_range)
                    return nic_ip


# for each node present in a group, it will be called
def update_db_nicinfo():
    db_data = {}
    for info in data["Categories"]:
        nic_nw = ""
        for category, value in info.items():
            if category_nm == category:
                cat_nm = category
                db_data['category'] = cat_nm
                for col in value:
                    for grp_key, grp_value in col.items():
                        for network in grp_value:
                            for net_key, net_value in network.items():
                                nic_nw = net_value.get('nicnetwork')
                                nic_nam = net_key
                                db_data[nic_nw] = nic_nam
                                nic_type = net_value.get('nictypes')
                                temp = nic_nw + '_type'
                                db_data[temp] = nic_type
                                temp = nic_nw + '_device'
                                if net_value.get('nicdevices'):
                                    nic_device = net_value.get('nicdevices')
                                    db_data[temp] = nic_device

                            nic_ip = generate_ip(nic_nw)
                            temp = nic_nw + '_ip'
                            db_data[temp] = str(nic_ip)
                insert_nicinfo_db.insert_nic_info(node_detail, db_data)


update_db_nicinfo()
