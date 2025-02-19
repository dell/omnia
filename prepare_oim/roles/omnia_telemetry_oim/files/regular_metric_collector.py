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

# regular_metric_collector.py
# !/usr/bin/env python3
'''
    Module to get all regular metrics
'''
import data_collector_psutil
import data_collector_smart
import data_collector_os
import invoke_commands
import common_parser
import utility
import data_collector_slurm
import prerequisite


class RegularMetricCollector:
    '''
    RegularMetricCollector class is responsible for collecting all regular metrics.
    '''

    def __init__(self):
        self.regular_metric_output_dict = {}
        self.regular_unit = {}

    def get_blocked_process(self):
        '''
        Retrieve blocked process information and store it in the dictionary.
        '''
        # Run the command to read /proc/stat and grep for procs_blocked
        command = "grep procs_blocked /proc/stat"
        output = invoke_commands.call_command(command)

        if output is not None:
            tokens = common_parser.split_by_regex(output, r"\s+")
            blocked_processes = tokens[1]

            # BlockedProcess is number of blocked processes waiting for I/O
            self.regular_metric_output_dict["BlockedProcesses"] = blocked_processes
            self.regular_unit["BlockedProcesses"] = "processes"
        else:
            self.regular_metric_output_dict["BlockedProcesses"] = utility.Result.NO_DATA.value

    def get_cpu_info(self):
        '''
        Retrieve CPU time information and store it in the dictionary.
        '''
        cputimes = data_collector_psutil.get_cpu_time_info()
        if cputimes is not None:
            # CPUSystem is CPU time spent in system mode
            self.regular_metric_output_dict["CPUSystem"] = str(cputimes.system)
            self.regular_unit["CPUSystem"] = "seconds"
            # CPUWait is CPU time spent in I/O wait mode
            self.regular_metric_output_dict["CPUWait"] = str(cputimes.iowait)
            self.regular_unit["CPUWait"] = "seconds"
        else:
            self.regular_metric_output_dict["CPUSystem"] = utility.Result.NO_DATA.value
            self.regular_metric_output_dict["CPUWait"] = utility.Result.NO_DATA.value


    def get_packet_errors(self):
        '''
        Retrieve packet error information and store it in the dictionary
        '''
        # Get network packet information
        netio = data_collector_psutil.get_packet_info()

        if netio is not None:
            # Start with an empty interface list
            interface_list = []

            # Dynamically check link status for each interface in netio
            for interface in netio.keys():
                try:
                    # Check link status using ethtool
                    ethtool_output = invoke_commands.call_command(f"ethtool {interface} | grep -i 'Link detected.*yes'")
                    if "yes" in ethtool_output.lower():
                        # Add interface to the list if the link is active
                        interface_list.append(interface)
                except Exception as e:
                    # Log or handle any errors during the ethtool call
                    print(f"Error checking link status for interface {interface}: {e}")

            # Process each interface in the updated interface list
            for interface in interface_list:
                values = netio.get(interface)
                if values is not None:
                    self.regular_metric_output_dict[f"ErrorsRecv:{interface}"] = str(values.errin)
                    self.regular_metric_output_dict[f"ErrorsSent:{interface}"] = str(values.errout)
                else:
                    self.regular_metric_output_dict[f"ErrorsRecv:{interface}"] = utility.Result.NO_DATA.value
                    self.regular_metric_output_dict[f"ErrorsSent:{interface}"] = utility.Result.NO_DATA.value

        else:
            # If netio data is not available, log no data for all metrics
            self.regular_metric_output_dict["ErrorsRecv"] = utility.Result.NO_DATA.value
            self.regular_metric_output_dict["ErrorsSent"] = utility.Result.NO_DATA.value

    def get_hardware_corrupted_memory(self):
        '''
        Retrieve HardwareCorrupted information and store it in the dictionary.
        '''
        # Run the command to grep for HardwareCorrupted in /proc/meminfo
        command = "grep HardwareCorrupted /proc/meminfo"
        output = invoke_commands.call_command(command)

        if output is not None:
            tokens = common_parser.split_by_regex(output, r"\s+")
            hardware_corrupted = tokens[1]

            # Hardware corrupted memory detected by ECC
            self.regular_metric_output_dict["HardwareCorruptedMemory"] = hardware_corrupted
            self.regular_unit["HardwareCorruptedMemory"] = "kB"
        else:
            self.regular_metric_output_dict["HardwareCorruptedMemory"] = utility.Result.NO_DATA.value

    def get_virtual_memory_info(self):
        '''
        Retrieve virtual memory information and store it in the provided dictionary.
        '''
        mem = data_collector_psutil.get_memory_info()
        if mem is not None:
            # MemoryFree is Free system memory
            self.regular_metric_output_dict["MemoryFree"] = str(mem.free)
            self.regular_unit["MemoryFree"] = "bytes"
            # MemoryTotal is Total memory on the system
            self.regular_metric_output_dict["MemoryTotal"] = str(mem.total)
            self.regular_unit["MemoryTotal"] = "bytes"
            # MemoryAvailable is Available memory on the system
            self.regular_metric_output_dict["MemoryAvailable"] = str(mem.available)
            self.regular_unit["MemoryAvailable"] = "bytes"
            # MemoryPercent is the percentage usage as ((total - available) / total) * 100
            self.regular_metric_output_dict["MemoryPercent"] = str(mem.percent)
            self.regular_unit["MemoryPercent"] = "percent"
            # MemoryUsed is memory used
            self.regular_metric_output_dict["MemoryUsed"] = str(mem.used)
            self.regular_unit["MemoryUsed"] = "bytes"
            # MemoryActive is memory currently in use
            self.regular_metric_output_dict["MemoryActive"] = str(mem.active)
            self.regular_unit["MemoryActive"] = "bytes"
            # MemoryInactive is memory that is marked as not used
            self.regular_metric_output_dict["MemoryInactive"] = str(mem.inactive)
            self.regular_unit["MemoryInactive"] = "bytes"
            # MemoryCached is cache for various things
            self.regular_metric_output_dict["MemoryCached"] = str(mem.cached)
            self.regular_unit["MemoryCached"] = "bytes"
            # MemoryShared is memory that may be simultaneously accessed by multiple processes
            self.regular_metric_output_dict["MemoryShared"] = str(mem.shared)
            self.regular_unit["MemoryShared"] = "bytes"
        else:
            self.regular_metric_output_dict["MemoryFree"] = utility.Result.NO_DATA.value
            self.regular_metric_output_dict["MemoryTotal"] = utility.Result.NO_DATA.value
            self.regular_metric_output_dict["MemoryAvailable"] = utility.Result.NO_DATA.value
            self.regular_metric_output_dict["MemoryPercent"] = utility.Result.NO_DATA.value
            self.regular_metric_output_dict["MemoryUsed"] = utility.Result.NO_DATA.value
            self.regular_metric_output_dict["MemoryActive"] = utility.Result.NO_DATA.value
            self.regular_metric_output_dict["MemoryInactive"] = utility.Result.NO_DATA.value
            self.regular_metric_output_dict["MemoryCached"] = utility.Result.NO_DATA.value
            self.regular_metric_output_dict["MemoryShared"] = utility.Result.NO_DATA.value

    def get_using_slurm(self):
        '''
        This method initiates slurm calls to data_collector_slurm and retrieves necessary values.
        '''
        # sinfo
        sinfo_dict = data_collector_slurm.get_cluster_values_sinfo()
        self.regular_metric_output_dict["NodesTotal"] = sinfo_dict["NodesTotal"]
        self.regular_metric_output_dict["NodesUp"] = sinfo_dict["NodesUp"]
        self.regular_metric_output_dict["NodesDown"] = sinfo_dict["NodesDown"]
        # squeue
        squeue_dict = data_collector_slurm.get_cluster_values_squeue()
        self.regular_metric_output_dict["QueuedJobs"] = squeue_dict["QueuedJobs"]
        self.regular_metric_output_dict["RunningJobs"] = squeue_dict["RunningJobs"]
        # sacct
        sacct_dict = data_collector_slurm.get_cluster_values_sacct()
        self.regular_metric_output_dict["FailedJobs"] = sacct_dict["FailedJobs"]

    def get_smart_regular_parameters(self):
        '''
        Get the following regular metric parameters:
        1. SMARTHDATemp
        '''
        SMARTHDATemp_dict = data_collector_smart.get_using_smartctl("SMARTHDATemp")
        for key in SMARTHDATemp_dict.keys():
            self.regular_metric_output_dict["SMARTHDATemp:" + key] = SMARTHDATemp_dict[key]
        self.regular_unit["SMARTHDATemp"] = "C"


    def get_unique_user_login(self):
        '''
        Get the following regular metric parameters:
        1. UniqueUserLogin
        '''
        self.regular_metric_output_dict["UniqueUserLogin"] = str(data_collector_os.get_unique_loggedin_users())

    def metric_collector(self, aggregation_level="compute"):
        '''
        This method aggregrates all the regular metric parameters.
        '''
        self.regular_metric_output_dict = {}
        self.get_blocked_process()
        self.get_cpu_info()
        self.get_packet_errors()
        self.get_hardware_corrupted_memory()
        self.get_virtual_memory_info()
        if prerequisite.dict_component_existence["smartctl"]:
            self.get_smart_regular_parameters()
        else:
            self.regular_metric_output_dict["SMARTHDATemp"] = utility.Result.NO_DATA.value

        # Get cluster level parameters.
        if aggregation_level in ["slurm_control_node", "slurm_control_node,login"]:
            if prerequisite.dict_component_existence["slurm"]:
                # Get following informations through slurm
                # 1.NodesDown
                # 2.NodesTotal
                # 3.NodesUp
                # 4.QueuedJobs
                # 5.RunningJobs
                # 6.FailedJobs
                self.get_using_slurm()
            else:
                self.regular_metric_output_dict["NodesTotal"] = utility.Result.NO_DATA.value
                self.regular_metric_output_dict["NodesUp"] = utility.Result.NO_DATA.value
                self.regular_metric_output_dict["NodesDown"] = utility.Result.NO_DATA.value
                self.regular_metric_output_dict["QueuedJobs"] = utility.Result.NO_DATA.value
                self.regular_metric_output_dict["RunningJobs"] = utility.Result.NO_DATA.value
                self.regular_metric_output_dict["FailedJobs"] = utility.Result.NO_DATA.value

        if aggregation_level in ["login", "slurm_control_node,login"]:
            # Get the Folloiwng parameter
            # 1. UniqueUserLogin
            self.get_unique_user_login()