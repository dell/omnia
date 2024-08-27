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
import subprocess
import calculate_ip_details

if len(sys.argv) <= 3:
    bmc_dynamic_range = sys.argv[1]
    dynamic_stanza = sys.argv[2]
# Pass proper variables
if len(sys.argv) > 3:
    discovery_ranges = sys.argv[1]
    discover_stanza = sys.argv[2]
    bmc_static_subnet = sys.argv[3]
    static_stanza = sys.argv[4]
    netmask_bits = sys.argv[5]
    bmc_static_range = sys.argv[6]


def cal_ranges(start_ip, end_ip):
    """
      Checks whether the bmc ranges given for bmcdiscovery is valid or not i.e. whether
      it is based on the nmap standards that xCAT supports

      Parameters:
          start_ip: Start ip of the range given.
          end_ip: End ip of the range given.

      Returns:
          range_status: bool value, whether the range provided is valid or not
          final_range: Final valid range in nmap format.
       """
    final_range = ""
    range_status = "true"
    for i in range(0, 3):
        if int(start_ip[i]) == int(end_ip[i]):
            final_range = final_range + start_ip[i] + "."
        elif int(start_ip[i]) < int(end_ip[i]):
            final_range = final_range + start_ip[i] + "-" + end_ip[i] + "."
        elif int(start_ip[i]) > int(end_ip[i]):
            print("Please provide a proper range")
            range_status = "false"
    if int(start_ip[3]) == int(end_ip[3]):
        final_range = final_range + start_ip[3]
    elif int(start_ip[3]) < int(end_ip[3]):
        final_range = final_range + start_ip[3] + "-" + end_ip[3]
    elif int(start_ip[3]) > int(end_ip[3]):
        print("Please provide a proper range")
        range_status = "false"
    return range_status, final_range


def create_ranges_dynamic(bmc_mode):
    """
        Calls the function to calculate and validate the ranges for dyanmic bmcdiscovery.

          Parameters:
              bmc_mode: What way bmc is getting discovered.

          Calls:
              if range is valid, call the function run_bmc_discover, for running bmcdiscovery.
       """
    temp = bmc_dynamic_range.split('-')
    start_ip = temp[0].split('.')
    end_ip = temp[1].split('.')
    output = cal_ranges(start_ip, end_ip)
    range_status = output[0]
    final_range = output[1]
    if range_status == "true":
        run_bmc_discover(final_range, dynamic_stanza, bmc_mode)


def create_ranges_static(bmc_mode):
    """
        Calls the function to calculate and validate the ranges for static bmcdiscovery.

          Parameters:
              bmc_mode: What way bmc is getting discovered.t

          Calls:
              if range is valid, call the function run_bmc_discover, for running bmcdiscovery.
       """
    temp = bmc_static_range.split('-')
    start_ip = temp[0].split('.')
    end_ip = temp[1].split('.')
    output = cal_ranges(start_ip, end_ip)
    range_status = output[0]
    final_range = output[1]
    if range_status == "true":
        run_bmc_discover(final_range, static_stanza, bmc_mode)


def create_ranges_discovery(bmc_mode):
    """
        Calls the function to calculate and validate the ranges for discovery bmcdiscovery.

          Parameters:
              bmc_mode: What way bmc is getting discovered.

          Calls:
            if range is valid, call the function run_bmc_discover, for running bmcdiscovery.
           """
    discover_range_list = discovery_ranges.split(',')
    for ip_range in discover_range_list:
        temp = ip_range.split('-')
        start_ip = temp[0].split('.')
        end_ip = temp[1].split('.')
        discover_subnet = calculate_ip_details.cal_ip_details(temp[0], netmask_bits)[1]
        if discover_subnet != bmc_static_subnet:
            output = cal_ranges(start_ip, end_ip)
            range_status = output[0]
            final_range = output[1]
            if range_status == "true":
                run_bmc_discover(final_range, discover_stanza, bmc_mode)

        elif discover_subnet == bmc_static_subnet:
            output = cal_ranges(start_ip, end_ip)
            range_status = output[0]
            final_range = output[1]
            if range_status == "true":
                run_bmc_discover(final_range, static_stanza, bmc_mode)


def run_bmc_discover(final_range, stanza_path, bmc_mode):
    """
        Calls the function to run bmcdiscovery over the ranges.

        Parameters:
          final_range: Valid range on which bmcdiscovery can be performed
          stanza_path: File in which bcmdiscovery result will be stored.
          bmc_mode: what way bmcs are getting discovered.
        Returns:
          Proper stanza file with results of bmcdiscovery, else it gets timed out.

    """
    command_list = ""
    if bmc_mode == "static" or bmc_mode == "discovery":
        command = f"/opt/xcat/bin/bmcdiscover --range {final_range} -z"
        command_list = command.split()
    elif bmc_mode == "dynamic":
        command = f"/opt/xcat/bin/bmcdiscover --range {final_range} -z -w"
        command_list = command.split()
    try:
        node_objs = subprocess.run(command_list, capture_output=True, timeout=600)
        with open(stanza_path, 'r+') as f:
            f.write(node_objs.stdout.decode())
    except subprocess.TimeoutExpired:
        print(
            "The discovery did not finish within the timeout period.Please provide a smaller range or a correct range.")


def create_ranges():
    """
            Calls the function to create ranges for different mtms discovery mode.
    """

    if len(sys.argv) > 3:
        if discovery_ranges != "0.0.0.0":
            bmc_mode = "discovery"
            create_ranges_discovery(bmc_mode)
        if bmc_static_range != "":
            bmc_mode = "static"
            create_ranges_static(bmc_mode)
    elif len(sys.argv) <= 3:
        if bmc_dynamic_range != "":
            bmc_mode = "dynamic"
            create_ranges_dynamic(bmc_mode)


create_ranges()
