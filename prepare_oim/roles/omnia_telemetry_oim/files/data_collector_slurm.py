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
Module to fetch parameters related to slurm.
'''

import common_parser
import invoke_commands
import common_logging
import utility

def get_cluster_values_sacct():
    '''
    get all sacct related values from this method.
    o/p:
        A dictionary "dict_cluster_parameter_sacct" with all required values.
        values retrieved from sacct:
            1.FailedJobs
    '''
    dict_cluster_parameter_sacct={}
    dict_cluster_parameter_sacct["FailedJobs"]=utility.Result.NO_DATA.value

    failed_jobs=0
    sacct_output = invoke_commands.call_command('sacct -P --delimiter=\t')
    if sacct_output is not None:
        try:
            parsed_dict_list_output_sacct = common_parser.get_dict_list_format_parser_output(sacct_output,"\t",1)
            column_list_state=parsed_dict_list_output_sacct["State"]
            for value in column_list_state:
                if value =="FAILED":
                    failed_jobs= failed_jobs+1
            dict_cluster_parameter_sacct["FailedJobs"]=str(failed_jobs)
        except Exception as err:
            common_logging.log_error("data_collector_slurm:get_cluster_values_sacct", "sacct command output parsing issue: " +str(type(err)) +" "+ str(err))
    else:
        common_logging.log_error("data_collector_slurm:get_cluster_values_sacct", "sacct command output is None")
    return dict_cluster_parameter_sacct

def get_cluster_values_sinfo():
    '''
    get all sinfo related values from this method.
    o/p:
        A dictionary "dict_cluster_parameter_sinfo" with all required values.
        values retrieved from sinfo:
            1.NodesUp
            2.NodesDown
            3.NodesTotal
    '''
    dict_cluster_parameter_sinfo={}
    dict_cluster_parameter_sinfo["NodesDown"]=utility.Result.NO_DATA.value
    dict_cluster_parameter_sinfo["NodesTotal"]=utility.Result.NO_DATA.value
    dict_cluster_parameter_sinfo["NodesUp"]=utility.Result.NO_DATA.value

    set_nodes_all=set([])
    set_nodes_up=set([])
    set_nodes_down=set([])
    sinfo_output = invoke_commands.call_command('sinfo --format=%N\t%P\t%a\t%C\t%t\t%D\t%m')
    slurm_down_states = ['down','drained','draining','fail','failing','future','inval','maint','powered_down','powering_down','unknown','unk']
    slurm_up_states = ['idle','mixed','completing']
    if sinfo_output is not None:
        try:
            parsed_dict_list_output_sinfo = common_parser.get_dict_list_format_parser_output(sinfo_output,"\t",1)
            column_list_state=parsed_dict_list_output_sinfo["STATE"]
            column_list_nodelist=parsed_dict_list_output_sinfo["NODELIST"]

            for index,node_state in enumerate (column_list_state):
                # state ending with * denotes node currently not responding, hence declaring that node as down.
                star_present = node_state.endswith('*')
                state = common_parser.split_by_regex(node_state, '\*')[0]
                for node in column_list_nodelist[index].split(','):
                    # Total Nodes
                    set_nodes_all.add(node)
                    # Nodes Up
                    if not star_present and state in slurm_up_states:
                        set_nodes_up.add(node)
                    # Nodes Down
                    elif star_present or state in slurm_down_states:
                        set_nodes_down.add(node)
            dict_cluster_parameter_sinfo["NodesDown"]=str(len(list(set_nodes_down)))
            dict_cluster_parameter_sinfo["NodesUp"]=str(len(list(set_nodes_up)))
            dict_cluster_parameter_sinfo["NodesTotal"]=str(len(list(set_nodes_all)))
        except Exception as err:
            common_logging.log_error("data_collector_slurm:get_cluster_values_sinfo", "sinfo command output parsing issue: " +str(type(err)) +" "+ str(err))
    else:
        common_logging.log_error("data_collector_slurm:get_cluster_values_sinfo", "sinfo command output is None")
    return dict_cluster_parameter_sinfo

def get_cluster_values_squeue():
    '''
    get all squeue related values from this method.
    o/p:
        A dictionary "dict_cluster_parameter_squeue" with all required values.
        values retrieved from squeue:
            1.QueuedJobs
            2.RunningJobs
    '''
    dict_cluster_parameter_squeue={}
    dict_cluster_parameter_squeue["QueuedJobs"]=utility.Result.NO_DATA.value
    dict_cluster_parameter_squeue["RunningJobs"]=utility.Result.NO_DATA.value

    running_jobs=0
    queued_jobs=0

    squeue_output = invoke_commands.call_command('squeue --format=%i\t%P\t%j\t%u\t%T\t%S\t%N')

    if squeue_output is not None:
        try:
            parsed_dict_list_output_squeue = common_parser.get_dict_list_format_parser_output(squeue_output,"\t",1)
            column_list_state=parsed_dict_list_output_squeue["STATE"]
            for value in column_list_state:
                #Running Jobs
                if value == "RUNNING":
                    running_jobs= running_jobs+1
                #Pending/Queued Jobs
                if value == "PENDING":
                    queued_jobs= queued_jobs+1
            dict_cluster_parameter_squeue["QueuedJobs"]=str(queued_jobs)
            dict_cluster_parameter_squeue["RunningJobs"]=str(running_jobs)
        except Exception as err:
            common_logging.log_error("data_collector_slurm:get_cluster_values_squeue", "squeue command output parsing issue: " +str(type(err)) +" "+ str(err))
    else:
        common_logging.log_error("data_collector_slurm:get_cluster_values_squeue", "squeue command output is None")
    return dict_cluster_parameter_squeue
