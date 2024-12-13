# Copyright 2024 Intel Corporation.
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
Module to gather gaudi metrics
'''
import shlex
import common_parser
import invoke_commands
import common_logging

def get_col_data(cmd_output, column):
    if cmd_output is None:
        return None
    return common_parser.get_col_from_df(cmd_output, column)

# --------------------------------Gaudi metric collection---------------------------------
def get_gaudi_metrics_output():
    '''
    This method collects command output for hl-smi command for gaudi metrics
    :return: gaudi query output
    '''
    gaudi_metrics_query = "hl-smi --query-aip=Name,driver_version,bus_id,power.draw,temperature.aip,utilization.aip --format=csv,nounits"
    command_result = invoke_commands.call_command(gaudi_metrics_query)
    if command_result is None:
        common_logging.log_error("data_collector_gaudi:get_gaudi_metrics_output",
                                 "hl-smi command did not give output for gaudi metrics.")
        return None
    return common_parser.get_df_format(command_result)

def get_gaudi_temp(gaudi_metrics_cmd_output):
    '''
    This method collects gaudi temp from gaudi query output
    :param gaudi_metrics_cmd_output: gaudi query output
    '''
    return get_col_data(gaudi_metrics_cmd_output, 'temperature.aip [C]')

def get_gaudi_utilization(gaudi_metrics_cmd_output):
    '''
    This method collects gaudi utilization from gaudi query output
    :param gaudi_metrics_cmd_output: gaudi query output
    '''
    return get_col_data(gaudi_metrics_cmd_output, 'utilization.aip [%]')

def get_gaudi_avg_utilization(gaudi_metrics_cmd_output):
    '''
    This method calculates average gaudi utilization on the node
    :param gaudi_metrics_cmd_output: gaudi query output
    '''
    gaudi_util_list = get_col_data(gaudi_metrics_cmd_output, 'utilization.aip [%]')
    if gaudi_util_list is not None and len(gaudi_util_list) != 0:
        return sum(gaudi_util_list)/len(gaudi_util_list)
    return None


# ------------------------------- Gaudi health metric collection-------------------------------
def get_gpu_health_driver(gaudi_metrics_cmd_output):
    '''
    This method collects gaudi driver health from gaudi query output
    '''
    return get_col_data(gaudi_metrics_cmd_output, 'driver_version')

def get_gpu_health_pcie(gaudi_metrics_cmd_output):
    '''
    This method collects gaudi pcie from gaudi query output
    '''
    return get_col_data(gaudi_metrics_cmd_output, 'bus_id')

def get_gpu_health_power(gaudi_metrics_cmd_output):
    '''
    This method collects gaudi power from gaudi query output
    '''
    gaudi_power_draw_list = get_col_data(gaudi_metrics_cmd_output, 'power.draw [W]')
    gaudi_pci_list = get_col_data(gaudi_metrics_cmd_output, 'bus_id')
    if gaudi_power_draw_list is None:
        return None,None
    if gaudi_pci_list is None:
        return None,None
    gaudi_power_limit_list = []
    for pci in gaudi_pci_list:
        pci = shlex.quote(pci).strip("'\"")
        cmd = ["hl-smi", "-q", "-d", "POWER", "-i", pci]
        '''
        grep "Power Limit" cannot work in the systemd process
        so just find the first "Power Limit" and use the substring
        Expected output should be like:
        ================ HL-SMI LOG ================
        ...
        "                Power Limit             : 550 W\n"
        ...
        find the line and capture the value 550
        '''
        power_limit_output = invoke_commands.run_command(cmd)
        if power_limit_output is None:
            return None,None
        prefix = "Power Limit"
        num_idx = power_limit_output.find(prefix)
        if num_idx == -1:
            return None,None
        power_limit_output = power_limit_output[num_idx:]
        prefix = ": "
        num_idx = power_limit_output.find(prefix)
        if num_idx == -1:
            return None,None
        num_idx += len(prefix)
        sub_str = power_limit_output[num_idx:]
        unit_idx = sub_str.find(" W")
        if unit_idx == -1:
            return None,None
        power_limit = sub_str[:unit_idx]
        try:
            float(power_limit)
        except ValueError:
            return None,None
        gaudi_power_limit_list.append(power_limit)
    if len(gaudi_power_limit_list) > 0:
        return (gaudi_power_limit_list, gaudi_power_draw_list)
    return None,None

def get_gpu_health_thermal(gaudi_metrics_cmd_output):
    '''
    This method collects gaudi thermal from gaudi query output
    '''
    return get_col_data(gaudi_metrics_cmd_output, 'temperature.aip [C]')