# Copyright 2023 Dell Inc. or its subsidiaries. All Rights Reserved.
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

import threading
import time
import os
import subprocess
import psycopg2
import re

node_details = {}

# MonitoringThread is a thread class which reads node details every 3 mins 
# and updates the same to postgresSQL database.
class MonitoringThread(threading.Thread):
    def run(self):
        node_details = get_node_details()
        add_details_to_db()

# get_node_details() function runs 2 commands on management station:
# nodels all nodelist.status : to check status of all nodes
# lsdef <nodename> | grep mac : to check mac address of the node
# These details are then stored in a dictionary format like: node_details[nodename]= [status, mac]
# where node_details is the dictionary name, nodename is the key to dictionary
# value corresponding to each key is an array comprising of node status and mac address
def get_node_details():
    node_status_cmd = '/opt/xcat/bin/nodels all nodelist.status'
    temp = subprocess.run([node_status_cmd], shell=True,capture_output=True,text=True)
    output = temp.stdout
    output = output.split("\n")
    for line in output:
        line = line.split(':')
        if len(line[0]) > 0:
            node_details[line[0]] = []
            node_details[line[0]].append(line[1].strip())
            
    for node in node_details.keys():
        node_details_cmd = '/opt/xcat/bin/lsdef' + ' ' + node + ' | grep mac='
        temp = subprocess.run([node_details_cmd], shell=True,capture_output=True,text=True)
        output = temp.stdout
        if len(output) > 0:
            node_details[node].append(output.split('=')[1].strip('\n'))
        else:
            node_details[node].append("")

    for node in node_details.keys():
        node_details_cmd = '/opt/xcat/bin/lsdef' + ' ' + node + ' | grep serial='
        temp = subprocess.run([node_details_cmd], shell=True,capture_output=True,text=True)
        output = temp.stdout
        if len(output) > 0:
            node_details[node].append(output.split('=')[1].strip('\n'))
        else:
            node_details[node].append("")
    return node_details


# add_details_to_db() function will connect to database and update database using following checks:
# It will check the status of node in DB. If status of node and current status is 'booted', nothing will be updated.
# Else, status of node in DB will be updated to current status.
# MAC of node will also be updated in DB if MAC address given by XCAT is a valid MAC address 
# and if current mac address is None. 
def add_details_to_db():
    conn = psycopg2.connect(
        database="omniadb",
        user='postgres',
        host='localhost',
        port='5432')
    conn.autocommit = True
    cursor = conn.cursor()
    for node in node_details.keys():
        sql_check_status = "Select status from cluster.nodeinfo where node = %s"
        cursor.execute(sql_check_status, (node,))
        current_status = cursor.fetchall()
        if current_status is not node_details[node][0]:
            sql_update_status = "Update cluster.nodeinfo set status = %s where node = %s"
            cursor.execute(sql_update_status, (node_details[node][0], node))
        sql_check_mac = "Select admin_mac from cluster.nodeinfo where node = %s"
        cursor.execute(sql_check_mac, (node,))
        current_mac = cursor.fetchall()
        if len(current_mac) < 2 and len(node_details[node][1]) > 2:
            if current_mac[0][0] is None and re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", node_details[node][1].lower()):
                sql_mac = "Update cluster.nodeinfo set admin_mac = %s where node = %s"
                cursor.execute(sql_mac, (node_details[node][1], node))
        sql_check_serial = "Select serial from cluster.nodeinfo where node = %s"
        cursor.execute(sql_check_serial, (node,))
        current_serial = cursor.fetchall()
        if len(current_serial) < 2 and len(node_details[node][2]) > 2:
            if current_serial[0][0] is None:
                sql_serial = "Update cluster.nodeinfo set serial = %s where node = %s"
                cursor.execute(sql_serial, (node_details[node][2], node))
    conn.close()

def main():
    try:
        MonitoringThreadObject = MonitoringThread()
        MonitoringThreadObject.Daemon = True
        MonitoringThreadObject.start()
    except Exception as e:
        print("Exception thrown by the monitoring thread:", e)
        sys.exit(1)

# Driver code
if __name__ == '__main__':
    main()
