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
Module to fetch parameters related to kubernetes.
'''

import common_parser
import invoke_commands
import common_logging
import utility

def get_kubectl_get_pods():
    '''
    Get the following parameters
        1.Kubernetespodsstatus:Is the status for all pods OK
    '''
    dict_cluster_parameter_kubectl_pods={}
    dict_cluster_parameter_kubectl_pods["Kubernetespodsstatus"]=utility.Result.UNKNOWN.value
    flag_kubernetes_pods_status="Unknown"
    output=invoke_commands.call_command('sudo kubectl get pods -A -o json')
    if output is not None:
        #Convert output to to json format
        pods_json=common_parser.get_json_format(output)
        if pods_json is not None:
            try:
                #Iterate over each entries in json. Each entry/item corresponds to individual pods of the command output : kubectl get pods -A
                total_pods=len(pods_json["items"])
                #Check if pod exists. If pod doesn't exist, output will be Unknown
                if total_pods > 0:
                    for index in range(total_pods):
                        #Get the status and check if it is "Running" or not
                        # Pod status
                        pod_status=pods_json["items"][index]["status"]["phase"]
                        # Container status
                        if "containerStatuses" in pods_json["items"][index]["status"].keys():
                            container_status_list=pods_json["items"][index]["status"]["containerStatuses"][0]["state"].keys()
                            # Pod and Container both should be running
                            if pod_status != "Running" or "running" not in container_status_list:
                                    # Not Running so Fail
                                    flag_kubernetes_pods_status= "False"
                                    break
                        else:
                            # Decide only based on the status of Pod
                            if pod_status != "Running":
                                flag_kubernetes_pods_status= "False"
                                break
                    if flag_kubernetes_pods_status == "False":
                        dict_cluster_parameter_kubectl_pods["Kubernetespodsstatus"]=\
                            utility.Result.FAILURE.value
                    else:
                        dict_cluster_parameter_kubectl_pods["Kubernetespodsstatus"]=\
                            utility.Result.SUCCESS.value
            except Exception as err:
                common_logging.log_error("data_collector_kubernetes:get_kubectl_get_pods",\
 "kubectl get pods -A json parsing issue: " + str(type(err)) +" "+ str(err))
        else:
            common_logging.log_error("data_collector_kubernetes:get_kubectl_get_pods",\
 "kubectl get pods -A json parsed output is None")
    else:
        common_logging.log_error("data_collector_kubernetes:get_kubectl_get_pods",\
 "kubectl get pods -A command output is None")
    return dict_cluster_parameter_kubectl_pods


def get_kubectl_get_nodes():
    '''
    Get the following parameters
        1.Kuberneteschildnode: Are all Kubernetes child nodes up
        2.kubernetesnodesstatus: Is the status for all Kubernetes nodes OK
    '''
    dict_cluster_parameter_kubectl_nodes={}
    dict_cluster_parameter_kubectl_nodes["Kuberneteschildnode"]=utility.Result.UNKNOWN.value
    dict_cluster_parameter_kubectl_nodes["kubernetesnodesstatus"]=utility.Result.UNKNOWN.value
    flag_child_nodes_up= "Unknown"
    flag_all_nodes_up= "Unknown"
    #index of status (type) in json output
    index_status=4
    output=invoke_commands.call_command('sudo kubectl get nodes -o json')
    if output is not None:
        nodes_json=common_parser.get_json_format(output)
        if nodes_json is not None:
            try:
                #Iterate over each entries in json. Each entry/item corresponds to individual nodes of the command output : kubectl get nodes
                total_nodes=len(nodes_json["items"])
                if total_nodes>0:
                    for index in range(total_nodes):
                        #Get the status and check if it is "Ready" or not
                        kubelet_status = next( key for key in nodes_json["items"][index]["status"]["conditions"] if key["type"] == "Ready")
                        if kubelet_status["status"] != "True":
                            flag_all_nodes_up = "False"
                            # In case single node is present, then that is both master and child node
                            if total_nodes==1:
                                flag_child_nodes_up = "False"
                            else:
                                #Check if non Ready node is a child node
                                if "node-role.kubernetes.io/master" not in nodes_json["items"][index]["metadata"]["labels"].keys():
                                    flag_child_nodes_up = "False"
                                    #break since we found non ready status in child nodes
                                    break
                #set the parameters
                #kubernetesnodesstatus
                if flag_all_nodes_up == "False":
                    dict_cluster_parameter_kubectl_nodes["kubernetesnodesstatus"]=\
                        utility.Result.FAILURE.value
                else:
                    dict_cluster_parameter_kubectl_nodes["kubernetesnodesstatus"]=\
                        utility.Result.SUCCESS.value
                #Kuberneteschildnode
                if flag_child_nodes_up == "False":
                    dict_cluster_parameter_kubectl_nodes["Kuberneteschildnode"]=\
                        utility.Result.FAILURE.value
                else:
                    dict_cluster_parameter_kubectl_nodes["Kuberneteschildnode"]=\
                        utility.Result.SUCCESS.value
            except Exception as err:
                common_logging.log_error("data_collector_kubernetes:get_kubectl_get_nodes",\
 "kubectl get nodes json parsing issue: " +str(type(err)) +" "+ str(err))
        else:
            common_logging.log_error("data_collector_kubernetes:get_kubectl_get_nodes",\
 "kubectl get nodes json parsed output is None")
    else:
        common_logging.log_error("data_collector_kubernetes:get_kubectl_get_nodes",\
 "kubectl get nodes command output is None")
    return dict_cluster_parameter_kubectl_nodes


def get_kubectl_get_cs():
    '''
    Get the following parameters
        1.kubernetescomponentsstatus: Get the component status
    '''
    dict_cluster_parameter_kubectl_cs={}
    dict_cluster_parameter_kubectl_cs["kubernetescomponentsstatus"]=\
        utility.Result.UNKNOWN.value

    output=invoke_commands.call_command('sudo kubectl get --raw=/livez?verbose')
    if output is not None:
        component_status = common_parser.query_from_txt(output, "healthz check (\\w+)")
        if component_status is not None:
            if component_status== "passed":
                dict_cluster_parameter_kubectl_cs["kubernetescomponentsstatus"]=\
                                            utility.Result.SUCCESS.value
            elif component_status== "failed":
                dict_cluster_parameter_kubectl_cs["kubernetescomponentsstatus"]=\
                                            utility.Result.FAILURE.value
        else:
            common_logging.log_error("data_collector_kubernetes:get_kubectl_get_cs","component healthz check information not found.")
    else:
        common_logging.log_error("data_collector_kubernetes:get_kubectl_get_cs","kubectl get --raw=/livez?verbose command output is None")
    return dict_cluster_parameter_kubectl_cs