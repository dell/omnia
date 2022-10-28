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
import ipaddress
from pandas import *

pxe_mapping_path = sys.argv[1]
ib_subnet = sys.argv[2]
roce_enabled = sys.argv[3]
ip = []
ib_ip = []


def ib_mapping_db():
    # Create a mapping file named pxe_mapping_file.csv
    data = read_csv(pxe_mapping_path)
    ip = data['IP'].tolist()
    ib_prefix = ib_subnet.split('.')[0] + '.' + ib_subnet.split('.')[1] + '.'
    conn = psycopg2.connect(
        database="omniadb",
        user='postgres',
        host='localhost',
        port='5432')
    conn.autocommit = True
    cursor = conn.cursor()
    for i in range(0, len(ip)):
        temp_ip = ip[i]
        temp = ib_prefix + ip[i].split('.')[2] + '.' + ip[i].split('.')[3]
        if roce_enabled == "False":
            sql = '''Update cluster.nodeinfo set ib_ip = inet'{temp}' where admin_ip = inet ('{temp_ip}') '''.format(
                temp=temp, temp_ip=temp_ip)
            cursor.execute(sql)
    conn.close()


ib_mapping_db()
