# Copyright 2022 Dell Inc. or its subsidiaries. All Rights Reserved.
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
import requests
import argparse
import psycopg2
import pandas
from pandas import *

pxe_mapping_path = sys.argv[1]
roce_status = sys.argv[2]
domain_name = sys.argv[3]
mac = []
hostname = []
ip = []


def mapping_file():
    # Create a mapping file named pxe_mapping_file.csv
    data = read_csv(pxe_mapping_path)
    mac = data['MAC'].tolist()
    hostname = data['Hostname'].tolist()
    ip = data['IP'].tolist()

    # Define the basic connection with omniadb which will be used with all the rest queries
    conn = psycopg2.connect(
        database="omniadb",
        user='postgres',
        host='localhost',
        port='5432')
    conn.autocommit = True
    cursor = conn.cursor()

    # Check if there exists any node with valid vendor
    for key in range(0, len(mac)):
        temp = mac[key]
        # Check if the mac address already exists in the table
        sql = '''select exists(select admin_mac from cluster.nodeinfo where admin_mac='{temp}')'''.format(temp=temp)
        cursor.execute(sql)
        output = cursor.fetchone()[0]
        fqdn_hostname = hostname[key] + "." + domain_name
        node = hostname[key]
        temp_ip = ip[key]
        # When roce is disabled
        if output is False and roce_status == "False":
            sql = '''INSERT INTO cluster.nodeinfo(admin_mac,node,hostname,admin_ip,bmc_ip,ib_ip) VALUES (
        '{temp}','{node}','{fqdn_hostname}','{temp_ip}',NULL,NULL)'''.format(temp=temp, node=node, fqdn_hostname=fqdn_hostname, temp_ip=temp_ip)
            cursor.execute(sql)

        # When roce is enabled
        if output is False and roce_status == "True":
            sql = '''INSERT INTO cluster.nodeinfo(admin_mac,node,hostname,admin_ip,bmc_ip,ib_ip) VALUES (
        '{temp}','{node}','{fqdn_hostname}',NULL,NULL,'{temp_ip}')'''.format(temp=temp, node=node, fqdn_hostname=fqdn_hostname, temp_ip=temp_ip)
            cursor.execute(sql)
    conn.close()


mapping_file()
