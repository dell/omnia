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

import re
import sys
import ipaddress
import pandas as pd

mapping_file_path = sys.argv[1]
admin_static_start_ip = sys.argv[2]
admin_static_end_ip = sys.argv[3]
mandatory_col = ["SERVICE_TAG", "ADMIN_MAC", "HOSTNAME", "ADMIN_IP", "BMC_IP"]
non_null_col = ["SERVICE_TAG", "ADMIN_MAC", "HOSTNAME", "ADMIN_IP"]
nan = float('nan')


def ip_within_range(ip):
    admin_start_ip = ipaddress.IPv4Address(admin_static_start_ip)
    admin_end_ip = ipaddress.IPv4Address(admin_static_end_ip)
    if ip < admin_start_ip or ip > admin_end_ip:
        print(ip)
        sys.exit("Please provide admin IP within the given admin static IP range " + str(ip))


def not_nan_val(ip):
    if pd.notna(ip):
        ipaddress.ip_address(ip)
        return True
    else:
        return False  # Treat NaN as invalid


def valid_st(df):
    for st in df['SERVICE_TAG']:
        if not str(st).isalnum():
            sys.exit("Please provide proper Service_tag" + st)


def valid_ip(df):
    nan = float('NaN')
    try:
        for ip in df['ADMIN_IP']:
            if not ipaddress.IPv4Address(ip):
                sys.exit("Please provide proper IP address. Expected 4 octets in" + ip)
            else:
                ip_within_range(ipaddress.IPv4Address(ip))

        for ip in df['BMC_IP']:
            out = not_nan_val(ip)
            if out and not ipaddress.IPv4Address(ip):
                sys.exit("Please provide proper IP address. Expected 4 octets in " + ip)

    except Exception as err:
        sys.exit(str(err))


def valid_mac(df):
    # Checks if admin_mac is of proper format or not
    pattern = r"^([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}$"
    for mac in df['ADMIN_MAC']:
        out = bool(re.match(pattern, mac.lower()))
        if not out:
            sys.exit("Please provide a valid admin mac address " + mac)


def unique_val_col(df):
    # Check if all the columns have unique values

    if df['SERVICE_TAG'].unique().size != df['SERVICE_TAG'].size:
        sys.exit("Please provide unique SERVICE_TAG")
    if df['ADMIN_MAC'].unique().size != df['ADMIN_MAC'].size:
        sys.exit("Please provide unique ADMIN_MAC")
    if df['HOSTNAME'].unique().size != df['HOSTNAME'].size:
        sys.exit("Please provide unique HOSTNAME")
    if df['ADMIN_IP'].unique().size != df['ADMIN_IP'].size:
        sys.exit("Please provide unique ADMIN_IP")

    bmc_unique_val = df['BMC_IP'].nunique()
    bmc_non_null_values = df['BMC_IP'].notnull().sum()
    if bmc_unique_val != bmc_non_null_values:
        sys.exit("Please provide unique BMC_IP")

    valid_st(df)
    valid_ip(df)
    valid_mac(df)


def validate_col(df):
    curr_cols = df.columns
    # Check if necessary columns are present or not.
    for i in mandatory_col:
        if i not in curr_cols:
            sys.exit(
                " Please provide a valid mapping file. It should contain SERVICE_TAG,ADMIN_MAC,HOSTNAME,ADMIN_IP,"
                "BMC_IP.")

    # Calculate null columns
    null_col_list = df.columns[df.isna().any()].tolist()
    for i in non_null_col:
        if i in null_col_list:
            sys.exit(" SERVICE_TAG,ADMIN_MAC,HOSTNAME and ADMIN_IP can't be null. Please provide proper values.")
    unique_val_col(df)


def read_mapping_csv():
    # def a function to read a csv file given a csv path
    try:
        csv_file = pd.read_csv(mapping_file_path)
        if len(csv_file) == 0:
            sys.exit("Please provide details in mapping file.")
        csv_file = csv_file.apply(lambda x: x.str.strip() if x.dtype == 'object' else x)
        csv_file.columns = csv_file.columns.str.strip()
        validate_col(csv_file)
    except pd.errors.ParserError as err:
        sys.exit("Some issue with the csv file: " + str(err))
    except Exception as err:
        sys.exit(str(err))


read_mapping_csv()
