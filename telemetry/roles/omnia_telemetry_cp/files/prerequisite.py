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

"""
This file holds functions related to prerequisite checking.
"""

import invoke_commands
import utility

dict_component_existence = {}

def get_system_name():
    '''Get system Serial no./Service Tag
    '''
    return invoke_commands.call_command('dmidecode -s system-serial-number')

def check_slurm_existence():
    '''
    Method to check slurm existence
    '''
    output =  invoke_commands.call_command('systemctl is-active slurmctld')
    if output is not None:
        dict_component_existence["slurm"] = True
    else:
        dict_component_existence["slurm"] = False

def check_kubernetes_existence():
    '''
    Method to check kubernetes existence
    '''
    output = invoke_commands.call_command("sudo kubectl version")
    if output is not None:
        dict_component_existence["kubernetes"] = True
    else:
        dict_component_existence["kubernetes"] = False

def check_nvidia_gpu_existence():
    '''
    Method to check whether nvidia GPU is present
    '''
    nvidia_output = invoke_commands.call_command_with_pipe("lspci|grep -i nvidia")
    if (nvidia_output is not None) and len(nvidia_output)>0:
        dict_component_existence["nvidiagpu"] = True
    else:
        dict_component_existence["nvidiagpu"] = False

def check_amd_gpu_existence():
    '''
    Method to check whether AMD GPU is present
    '''
    amd_output = invoke_commands.call_command_with_pipe\
                ("lspci|grep \"Display controller: Advanced Micro Devices, Inc. \[AMD/ATI\]\"")
    if (amd_output is not None) and len(amd_output)>0:
        dict_component_existence["amdgpu"] = True
    else:
        dict_component_existence["amdgpu"] = False

def check_beegfs_existence():
    '''
    Method to check whether beegfs is present
    '''
    output  =  invoke_commands.run_command("systemctl is-active beegfs-client")
    if output is not None and output in ("failed", "active"):
        dict_component_existence["beegfs"] = True
    else:
        dict_component_existence["beegfs"] = False

def check_smartctl_existence():
    '''
        Method to check whether smarmontools is installed or not
    '''
    output =  invoke_commands.call_command("smartctl -V")
    if output is not None:
        dict_component_existence["smartctl"] = True
    else:
        dict_component_existence["smartctl"] = False

def check_component_existence():
    '''check if required component are installed or not'''

    global dict_component_existence
    dict_component_existence = {}

    if utility.dict_telemetry_ini["group_info"] in ["manager", "manager,login"]:
        check_slurm_existence()
        check_kubernetes_existence()

    check_nvidia_gpu_existence()
    check_amd_gpu_existence()
    check_beegfs_existence()
    check_smartctl_existence()
