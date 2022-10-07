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

import logging
import sys
import time
import datetime
import inspect
import easysnmp
from easysnmp import Session
from collections import defaultdict
import requests
import argparse
import ipaddress
import csv

# Define global variables
switch_ip = sys.argv[1]
switch_string = sys.argv[2]
pxe_start_range = sys.argv[3]
pxe_end_range = sys.argv[4]
node_name = sys.argv[5]
pxe_mapping_path = sys.argv[6]
domain_name = sys.argv[7]
temp_decimal_oids = []
hexa_mac = []
final_mac = {}
valid_mac = []


def collect_dec_oid():
    # Create an SNMP session to be used for all our requests
    session = Session(hostname=switch_ip, community=switch_string, version=2)

    # Run snmp walk on the created session
    description = session.walk('.1.3.6.1.2.1.17.7.1.2.2.1.2')

    # Collect information about the temp decimal MACs/oids
    for item in description:
        temp_decimal_oids.append(item.oid)

    filter_dec_oid()


def filter_dec_oid():
    count = 1
    temp_oids = []

    # Extract the last 6 digit that forms the decimal MAC
    for item in temp_decimal_oids:
        temp_oids.append(item.split('-')[1])

    for item in temp_oids:
        temp_nos = []
        # Convert decimal to hexadecimal numbers
        for i in item.split('.'):
            number = format(int(i), 'x')
            #                       print (number)
            # To append 0 as MAC has 00 instead of 0
            if number == "0":
                number = "0" + number
            temp_nos.append(number)
        hexa_mac.append(temp_nos[-6:])
        count = count + 1

    final_hex_mac()


def final_hex_mac():
    count = 1
    for row1 in hexa_mac:
        temp = ""
        for value in row1:
            # To append 0 as MAC has single digit number instead of 0
            if value.isnumeric() is True and 9 >= int(value) > 0:
                value = "0" + value
            temp = temp + value + ":"
        final_mac[count] = temp[:-1]
        count = count + 1
    for key in final_mac:
        identify_device_type(final_mac[key])


def identify_device_type(mac_address):
    url = "https://api.macvendors.com/"
    # Use get method to fetch details
    response = requests.get(url + mac_address)
    if response.status_code != 200:
        raise Exception("[!] Invalid MAC Address!")
    if "Broadcom" in response.content.decode() or "Intel" in response.content.decode():
        valid_mac.append(mac_address)
        print(response.content.decode())
    else:
        print(response.content.decode() + " : Not a valid device type")

    mapping_file_creation()


def mapping_file_creation():
    rows = []
    count = 0
    ip_addr = ipaddress.IPv4Address(pxe_start_range)
    fields = ['MAC', 'Hostname', 'IP']

    # Create a mapping file named pxe_mapping_file.csv
    filename = pxe_mapping_path

    # for each valid mac address insert hostname and ip in mapping file
    for key in valid_mac:
        temp = []
        temp.append(key)
        host_name = node_name + str(count)
        count = '%05d' % (int(count) + 1)
        host_name = node_name + str(count) + "." + domain_name
        temp.append(host_name)

        # Check whether new static IP is within the pxe ranges
        if ip_addr < ipaddress.IPv4Address(pxe_end_range):
            temp.append(ip_addr)
        else:
            print(" Provide proper pxe ranges and IP has gone out of range!!")
            break
        ip_addr = ip_addr + 1
        rows.append(temp)
    # Open file and write for mapping file
    with open(filename, 'w') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(fields)
        csvwriter.writerows(rows)
    csvfile.close()


collect_dec_oid()
