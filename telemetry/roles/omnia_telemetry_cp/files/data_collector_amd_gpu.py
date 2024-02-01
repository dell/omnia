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
Module to gather amd gpu metrics
'''

import common_parser
import invoke_commands
import common_logging

# --------------------------------AMD GPU metric collection---------------------------------

def get_amd_gpu_temp():
    '''
    This method collects amd gpu temp from rocm query output
    and stores it in gpu metric dictionary
    '''
    amd_metrics_query = "rocm-smi -t --csv"
    command_result = invoke_commands.run_command(amd_metrics_query)
    if command_result is not None:
        gpu_temp = {}
        command_result_df = common_parser.get_df_format(command_result)
        try:
            gpu_temp['sensor_edge'] = common_parser.get_col_from_df(command_result_df,
                                                                'Temperature (Sensor edge) (C)')
        except Exception as err:
            gpu_temp['sensor_edge'] = None
            common_logging.log_error("data_collector_amd_gpu:get_amd_gpu_temp",
                                     "could not parse sensor_edge temp from rocm-smi" + str(err))
        try:
            gpu_temp['sensor_junction'] = common_parser.get_col_from_df(command_result_df,
                                                             'Temperature (Sensor junction) (C)')
        except Exception as err:
            gpu_temp['sensor_junction'] = None
            common_logging.log_error("data_collector_amd_gpu:get_amd_gpu_temp",
                                "could not parse sensor_junction temp from rocm-smi" + str(err))
        try:
            gpu_temp['sensor_memory'] = common_parser.get_col_from_df(command_result_df,
                                                                 'Temperature (Sensor memory) (C)')
        except Exception as err:
            gpu_temp['sensor_memory'] = None
            common_logging.log_error("data_collector_amd_gpu:get_amd_gpu_temp",
                                   "could not parse sensor_memory temp from rocm-smi" + str(err))
        try:
            gpu_temp['sensor_hbm0'] = common_parser.get_col_from_df(command_result_df,
                                                                'Temperature (Sensor HBM 0) (C)')
        except Exception as err:
            gpu_temp['sensor_hbm0'] = None
            common_logging.log_error("data_collector_amd_gpu:get_amd_gpu_temp",
                                     "could not parse sensor_hbm0 temp from rocm-smi" + str(err))
        try:
            gpu_temp['sensor_hbm1'] = common_parser.get_col_from_df(command_result_df,
                                                                'Temperature (Sensor HBM 1) (C)')
        except Exception as err:
            gpu_temp['sensor_hbm1'] = None
            common_logging.log_error("data_collector_amd_gpu:get_amd_gpu_temp",
                                     "could not parse sensor_hbm1 temp from rocm-smi" + str(err))
        try:
            gpu_temp['sensor_hbm2'] = common_parser.get_col_from_df(command_result_df,
                                                                'Temperature (Sensor HBM 2) (C)')
        except Exception as err:
            gpu_temp['sensor_hbm2'] = None
            common_logging.log_error("data_collector_amd_gpu:get_amd_gpu_temp",
                                     "could not parse sensor_hbm2 temp from rocm-smi" + str(err))
        try:
            gpu_temp['sensor_hbm3'] = common_parser.get_col_from_df(command_result_df,
                                                                'Temperature (Sensor HBM 3) (C)')
        except Exception as err:
            gpu_temp['sensor_hbm3'] = None
            common_logging.log_error("data_collector_amd_gpu:get_amd_gpu_temp",
                                     "could not parse sensor_hbm3 temp from rocm-smi" + str(err))
        return gpu_temp

    common_logging.log_error("data_collector_amd_gpu:get_amd_gpu_temp",
                             "rocm-smi command did not give output for gpu temperature metrics.")
    return None

def get_amd_gpu_utilization():
    '''
    This method collects amd gpu utilization from rocm query output
    and stores it in gpu metric dictionary
    '''
    amd_metrics_query = "rocm-smi -u --csv"
    command_result = invoke_commands.run_command(amd_metrics_query)
    if command_result is not None:
        try:
            command_result_df = common_parser.get_df_format(command_result)
            gpu_util_list = common_parser.get_col_from_df(command_result_df, 'GPU use (%)')
            return gpu_util_list
        except Exception as err:
            common_logging.log_error("data_collector_amd_gpu:get_amd_gpu_utilization",
                                     "could not parse gpu utilization from rocm-smi"+str(err))
            return None
    return None


def get_amd_gpu_avg_utilization(gpu_util_list):
    '''
    This method calculates average gpu utilization on the node
    and stores it in gpu metric dictionary
    '''
    if gpu_util_list is not None:
        try:
            gpu_average_utilization = sum(gpu_util_list)/len(gpu_util_list)
            return gpu_average_utilization
        except Exception as err:
            common_logging.log_error("data_collector_amd_gpu:get_amd_gpu_avg_utilization",
                                     "could not calculate gpu utilization from rocm-smi"+str(err))
            return None
    return None

# -------------------------------AMD GPU health metric collection-------------------------------

def get_gpu_health_driver():
    '''
    This method collects amd gpu driver health from rocm query output
    '''
    amd_metrics_query = "rocm-smi --showdriverversion --csv"
    command_result = invoke_commands.run_command(amd_metrics_query)
    list_info = invoke_commands.run_command("rocm-smi -i --csv")
    gpu_driver = {}
    if command_result is not None and list_info is not None:
        try:
            command_result_df = common_parser.get_df_format(command_result)
            gpu_util_list = common_parser.get_col_from_df(command_result_df, 'Driver version')
            list_info_df = common_parser.get_df_format(list_info)
            gpu_list = common_parser.get_col_from_df(list_info_df, 'GPU ID')
            for index,item in enumerate(gpu_list):
                gpu_driver[index] = gpu_util_list[0]
            return gpu_driver
        except Exception as err:
            common_logging.log_error("data_collector_amd_gpu:get_gpu_health_driver",
                                     "could not parse gpu driver health from rocm-smi. "+str(err))
            return None
    return None

def get_gpu_health_nvlink():
    '''
    This method collects amd gpu nvlink health from rocm query output
    '''
    gpu_util = None
    return gpu_util

def get_gpu_health_pcie():
    '''
    This method collects amd gpu pcie health from rocm query output
    '''
    amd_metrics_query = "rocm-smi --showbus --csv"
    command_result = invoke_commands.run_command(amd_metrics_query)
    if command_result is not None:
        try:
            command_result_df = common_parser.get_df_format(command_result)
            gpu_util_list = common_parser.get_col_from_df(command_result_df, 'PCI Bus')
            return gpu_util_list
        except Exception as err:
            common_logging.log_error("data_collector_amd_gpu:get_gpu_health_pcie",
                                     "could not parse gpu pcie health from rocm-smi. "+str(err))
            return None
    return None

def get_gpu_health_pmu():
    '''
    This method collects amd gpu pmu health from rocm query output
    '''
    gpu_util = None
    return gpu_util

def get_gpu_health_power():
    '''
    This method collects amd gpu power health from rocm query output
    '''
    amd_metrics_query = "rocm-smi -P -M --csv"
    command_result = invoke_commands.run_command(amd_metrics_query)
    if command_result is not None:
        try:
            command_result_df = common_parser.get_df_format(command_result)
            gpu_util_list_max = common_parser.get_col_from_df(command_result_df,
                                                              'Max Graphics Package Power (W)')
            gpu_util_list_avg = common_parser.get_col_from_df(command_result_df,
                                                              'Average Graphics Package Power (W)')
            return gpu_util_list_max,gpu_util_list_avg
        except Exception as err:
            common_logging.log_error("data_collector_amd_gpu:get_gpu_health_power",
                                     "could not parse gpu power health from rocm-smi. "+str(err))
            return None,None
    return None,None

def get_gpu_health_thermal():
    '''
    This method collects amd gpu thermal health from rocm query output
    '''
    amd_metrics_query = "rocm-smi -t --csv"
    command_result = invoke_commands.run_command(amd_metrics_query)
    if command_result is not None:
        command_result_df = common_parser.get_df_format(command_result)
        try:
            gpu_temp = common_parser.get_col_from_df(command_result_df,
                                                                'Temperature (Sensor edge) (C)')
            return gpu_temp
        except Exception as err:
            common_logging.log_error("data_collector_amd_gpu:get_gpu_health_thermal",
                                     "could not parse sensor_edge temp from rocm-smi. " + str(err))
        return None
    return None
