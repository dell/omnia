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
import easysnmp
from easysnmp import Session
from collections import defaultdict
import requests
import argparse
import ipaddress
import csv
import psycopg2
import os

bmc_start_range = sys.argv[1]
bmc_end_range = sys.argv[2]


def bmc_db_insertion():
    count = 0
    ip_start_addr = ipaddress.IPv4Address(bmc_start_range) - 1
    ip_end_addr = ipaddress.IPv4Address(bmc_end_range)

    conn = psycopg2.connect(
        database="omniadb",
        user='postgres',
        host='localhost',
        port='5432')
    conn.autocommit = True
    cursor = conn.cursor()
    sql = '''Update cluster.nodeinfo set bmc_ip=inet '{ip_start_addr}'+ id where node!='control_plane';'''.format(ip_start_addr=ip_start_addr)
    cursor.execute(sql)
    conn.close()


bmc_db_insertion()
