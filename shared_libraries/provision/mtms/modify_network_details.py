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
	Extracts the bmc IP and serial of the nodes from the stanza file.

	Parameters:
	- stanza_path (str): The path to the stanza file.

	Returns:
	- bmc (list): A list of bmc IPs.
	- serial (list): A list of serial numbers.

	This function reads the stanza file and extracts the bmc IP and serial number of the nodes.
	It iterates over each line in the file and checks if the line contains 'serial=' or 'bmc=',
	indicating the presence of the serial number or bmc IP.
	If the line contains 'serial=', it splits the line on '=' and appends the last element
	(the serial number) to the 'serial' list.
	If the line contains 'bmc=', it splits the line on '=' and appends the last element
	(the bmc IP) to the 'bmc' list.

	The function returns the 'bmc' and 'serial' lists.
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
	Update the node object name in stanzas file.

	Parameters:
	- service_tag (str): The service tag of the node.
	- nodename (str): The new name of the node.
	- stanza_path (str): The path to the stanza file.

	Returns:
	- None

	This function updates the node object name in the stanzas file by replacing the existing service tag with the new nodename.
	It opens the stanza file in read and write mode, reads the file, replaces the existing service tag with the new nodename,
	and writes the updated content back to the file.
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
	- cursor: Pointer to omniadb DB.
	- temp_bmc_ip: bmc_ip whose presence we need to check in DB.

	Returns:
	- bool: that gives true or false if the bmc ip is present in DB.
	"""

    query = "SELECT EXISTS(SELECT bmc_ip FROM cluster.nodeinfo WHERE bmc_ip=%s)"
    cursor.execute(query, (str(temp_bmc_ip),))
    output = cursor.fetchone()[0]
    return output


def check_presence_admin_ip(cursor, temp_admin_ip):
    """
	Checks the presence of a given admin IP in the cluster.nodeinfo table.

	Parameters:
	- cursor (cursor): The cursor object used to execute the SQL query.
	- temp_admin_ip (str): The admin IP to check.

	Returns:
	- bool: True if the admin IP is present, False otherwise.
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
	- cursor (cursor): Pointer to omniadb DB.
	- uncorrelated_admin_start_ip (str): In case correlation doesn't work, from where we should start assigning the IP.
	- admin_static_start_range (str): Admin static start ip.
	- admin_static_end_range (str): Admin static end ip.
	- discovery_mechanism (str): Which mode we are using for discovering the nodes.

	Returns:
	- admin_ip (ipaddress.IPv4Address): A valid uncorrelated admin_ip for the node.
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
	Reassigns a BMC IP address if the reassignment status is true.

	Parameters:
	- cursor (cursor): Pointer to the nodeinfo DB.
	- bmc_static_start_ip (str): BMC static start IP.
	- bmc_static_end_ip (str): BMC static end IP.

	Returns:
	- str: A valid BMC IP for the node.

	This function iterates over the BMC IP addresses and checks if each IP is present in the DB.
	If it is not present, the function returns the BMC IP.
	If it is present, the function increments the IP and checks if it is less than the end IP.
	If it is, the function continues the loop.
	If it is not, the function exits the program and prints an error message.
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
