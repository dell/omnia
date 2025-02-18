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

import ipaddress
import sys
from psycopg2.extensions import AsIs

"""
    This module provides functionality for calculating and
    validating the uncorrelated admin IP for a node.
"""

def cal_nic_ip(cursor, col, ip, end_ip):
    """
    Calculates the uncorrelated network interface IP for a node.

    Args:
        cursor (psycopg2.extensions.cursor): A cursor object for executing SQL queries.
        col (str): The column name in the database.
        ip (str): The starting IP address.
        end_ip (str): The ending IP address.

    Returns:
        str: The uncorrelated network interface IP.

    Raises:
        SystemExit: If the end of the IP range is reached.

    """
    end_ip = ipaddress.IPv4Address(end_ip)
    op = check_presence_ip(cursor, col, ip)
    if not op:
        nic_ip = ipaddress.IPv4Address(ip)
        return str(nic_ip)
    elif op:
        while True:
            ip = ipaddress.IPv4Address(ip) + 1
            nic_ip = ip
            output = check_presence_ip(cursor, col, nic_ip)
            if not output and nic_ip < end_ip:
                break
            else:
                sys.exit(
                    "We have reached the end of ranges. Please do a cleanup and provide a wider nic_range, if more nodes needs to be discovered.")

        return str(nic_ip)
def check_presence_ip(cursor, col, ip):
    """
        Check presence of bmc ip in DB.
        Parameters:
            cursor: Pointer to omniadb DB.
            col: the col name in the DB
            ip: ip whose presence we need to check in DB.
        Returns:
            bool: that gives true or false if the bmc ip is present in DB.
    """
    query = '''SELECT EXISTS(SELECT %s FROM cluster.nicinfo WHERE %s=%s)'''
    cursor.execute(query, (AsIs(f"{col}_ip"), AsIs(f"{col}_ip"), str(ip)))
    output = cursor.fetchone()[0]
    return output



def cal_uncorrelated_add_ip(cursor, col, nic_mode, nic_range):
    """
      Calculates the uncorrelated node admin ip, if correlation is false, or it is not possible.
      Parameters:
          cursor: Pointer to omniadb DB.
          col: In case correlation doesn't work, from where we should start assigning the IP.
          nic_mode: Whether static or cidr format given for ranges
          nic_range: static range for assigning network interface ip.
      Returns:
          nic_ip: A valid uncorrelated admin_ip for the node.
    """
    # create start and end ip
    start_nic_ip = nic_range.split('-')[0]
    start_nic_ip = ipaddress.IPv4Address(start_nic_ip)
    end_nic_ip = nic_range.split('-')[1]
    end_nic_ip = ipaddress.IPv4Address(end_nic_ip)
    cursor.execute("SELECT EXISTS(SELECT 1 FROM cluster.nicinfo LIMIT 1)")
    rows_exist = cursor.fetchone()[0]
    if nic_mode == "static":
        if rows_exist:
            sql = f'''select %s from cluster.nicinfo where %s is not NULL ORDER BY %s  DESC LIMIT 1'''
            cursor.execute(sql, (AsIs(f"{col}_ip"), AsIs(f"{col}_ip"), AsIs(f"{col}_ip")))
            last_nic_ip = cursor.fetchone()
            if last_nic_ip is None:
                return str(start_nic_ip)
            elif start_nic_ip <= ipaddress.IPv4Address(last_nic_ip[0]) <= end_nic_ip:
                nic_ip = cal_nic_ip(cursor, col, last_nic_ip[0], str(end_nic_ip))
                return str(nic_ip)
        else:
            return str(start_nic_ip)
    if nic_mode == "cidr":
        if rows_exist:
            sql = f'''select %s from cluster.nicinfo where %s is not NULL ORDER BY %s  DESC LIMIT 1'''
            cursor.execute(sql, (AsIs(f"{col}_ip"), AsIs(f"{col}_ip"), AsIs(f"{col}_ip")))
            last_nic_ip = cursor.fetchone()
            if last_nic_ip is None:
                return str(start_nic_ip)
            elif start_nic_ip <= ipaddress.IPv4Address(last_nic_ip[0]) <= end_nic_ip:
                nic_ip = cal_nic_ip(cursor, col, last_nic_ip[0], str(end_nic_ip))
                return str(nic_ip)
        else:
            return str(start_nic_ip)
