# Copyright 2023 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
Module to fetch miscellaneous parameters that does not require parsing.
'''

import invoke_commands
import common_logging
import utility

def get_beegfs_version():
    '''
          Returns whether beegfs client is present or not
    '''
    beegfs_service_status = 'systemctl is-active beegfs-client'
    output = invoke_commands.run_command(beegfs_service_status)
    if output is not None:
        if output == "failed":
            common_logging.log_error("data_collector_storage:get_beegfs_version",
                                     "beegfs gave errors" + output)
            return 0
        if output == "active":
            return 1
    return -1

def get_beegfs_details():
    '''
             Returns whether beegfs client is reachable or not
    '''
    error_str = 'Command not found'
    beegfs_op_dict = {}
    beegfs_op_dict["Beegfs client Reachable"] = utility.Result.UNKNOWN.value
    beegfs_status = get_beegfs_version()
    beegfs_cmd = 'beegfs-ctl --nodetype=client --listnodes'
    output = invoke_commands.run_command(beegfs_cmd)
    hostname = utility.get_system_hostname()
    if beegfs_status == 1 and output is not None:
        if hostname is not None and hostname in output:
            beegfs_op_dict["Beegfs client Reachable"] = utility.Result.SUCCESS.value
        else:
            beegfs_op_dict["Beegfs client Reachable"] = utility.Result.FAILURE.value
            common_logging.log_error("data_collector_storage:get_beegfs_details",
                                     "beegfs gave errors" + output)
    elif beegfs_status == 0 and output is not None:
        beegfs_op_dict["Beegfs client Reachable"] = utility.Result.FAILURE.value
        common_logging.log_error("data_collector_storage:get_beegfs_details",
                                 "beegfs gave errors" + output)
    else:
        common_logging.log_error("data_collector_storage:get_beegfs_details",
                                 "beegfs gave error" + error_str)

    return beegfs_op_dict