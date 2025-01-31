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
import sys
import re
oim = "oim"


def extract_serial_bmc(stanza_path):
    """
         Extract the bmc IP and serial of the nodes from the stanza file.
          Parameters:
              stanza_path (str): The path of the file where bmcdiscover results are stored
          Returns:
              bmc: List of bmc_ips present in stanza file.
              serial: List of serial/service_tags present in stanza file.
    """
    serial = []
    bmc = []
    # Extract the bmc IP and serial of the nodes from the stanza file
    file = open(stanza_path)
    for line in file:
        if 'serial=' in line:
            temp = line.split("=")[-1].strip()
            serial.append(temp)
        if 'bmc=' in line:
            bmc.append(line.split("=")[-1].strip())
    file.close()
    return bmc, serial


def update_stanza_file(service_tag, nodename, stanza_path):
    """
       Update the node object name in stanzas file
       Parameters:
           service_tag: Service tag of the node that needs the update.
           nodename: The new node name that the node obj gets and updating it in stanza path
           stanza_path (str): The path of the file where bmcdiscover results are stored
       Returns:
           file gets updated with proper node name.
    """
    # Update the node object name in stanzas file
    with open(stanza_path, "r+") as file:
        data = file.read()
        rep_text = re.sub(f'node-.*-{service_tag}:', f'{nodename}' + ':', data)
        file.seek(0)
        file.truncate()
        file.write(rep_text)
        file.close()


def check_presence_bmc_ip(cursor, temp_bmc_ip):
    """
         Check presence of bmc ip in DB.
         Parameters:
             cursor: Pointer to omniadb DB.
             temp_bmc_ip: bmc_ip whose presence we need to check in DB.
         Returns:
             bool: that gives true or false if the bmc ip is present in DB.
    """

    query = "SELECT EXISTS(SELECT bmc_ip FROM cluster.nodeinfo WHERE bmc_ip=%s)"
    cursor.execute(query, (str(temp_bmc_ip),))
    output = cursor.fetchone()[0]
    return output


def check_presence_admin_ip(cursor, temp_admin_ip):
    """
     Check presence of admin ip in DB.
     Parameters:
         cursor: Pointer to omniadb DB.
         temp_admin_ip: admin_ip whose presence we need to check in DB.
     Returns:
         bool: that gives true or false if the admin ip is present in DB.
    """
    query = "SELECT EXISTS(SELECT admin_ip FROM cluster.nodeinfo WHERE admin_ip=%s)"
    cursor.execute(query, (str(temp_admin_ip),))
    output = cursor.fetchone()[0]
    return output


def cal_uncorrelated_admin_ip(cursor, uncorrelated_admin_start_ip, admin_static_start_range, admin_static_end_range,
                              discovery_mechanism):
    """
      Calculates the uncorrelated node admin ip, if correlation is false, or it is not possible.
      Parameters:
          cursor: Pointer to omniadb DB.
          uncorrelated_admin_start_ip: In case correlation doesn't work, from where we should start assigning the IP.
          admin_static_start_range: Admin static start ip
          admin_static_end_range: Admin static end ip
          discovery_mechanism: Which mode we are using for discovering the nodes
      Returns:
          admin_ip: A valid uncorrelated admin_ip for the node.
    """

    sql = f'''select admin_ip from cluster.nodeinfo where node!='oim' ORDER BY id DESC LIMIT 1'''
    cursor.execute(sql)
    last_admin_ip = cursor.fetchone()
    uncorr_output = check_presence_admin_ip(cursor, uncorrelated_admin_start_ip)
    if last_admin_ip is None or not uncorr_output:
        admin_ip = ipaddress.IPv4Address(uncorrelated_admin_start_ip)
        return admin_ip
    elif uncorr_output:
        while True:
            uncorrelated_admin_start_ip = ipaddress.IPv4Address(uncorrelated_admin_start_ip) + 1
            admin_ip = ipaddress.IPv4Address(uncorrelated_admin_start_ip)
            output = check_presence_admin_ip(cursor, admin_ip)
            if not output:
                break
            elif admin_ip > admin_static_end_range:
                sys.exit(
                    "We have reached the end of admin_static_ranges. Please do a cleanup and provide a wider range, if more nodes needs to be discovered.")
        return admin_ip


def reassign_bmc_ip(cursor, bmc_static_start_ip, bmc_static_end_ip):
    """
         Reassign some bmc_ip if the reassignment status is true.
          Parameters:
             cursor: pointer to the nodeinfo DB.
             bmc_static_start_ip: bmc static start ip
             bmc_static_end_ip: bmc static end ip
          Returns:
              a valid bmc_ip for the node.
    """
    temp_bmc_ip = bmc_static_start_ip
    while True:
        output = check_presence_bmc_ip(cursor, temp_bmc_ip)
        if not output:
            return temp_bmc_ip
        elif output and temp_bmc_ip < bmc_static_end_ip:
            temp_bmc_ip = ipaddress.IPv4Address(temp_bmc_ip) + 1
        elif temp_bmc_ip > bmc_static_end_ip:
            sys.exit(
                "We have reached the end of bmc_static_ranges. Please do a cleanup and provide a wider range, if more nodes needs to be discovered.")
