"""
MIT License
Copyright (c) 2022 Texas Tech University
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
This file is part of MonSter.
Author:
    Jie Li, jie.li@ttu.edu
"""

import json
import logger
import hostlist


log = logger.get_logger(__name__)

def parse_jobs_metrics(jobs_data: dict,
                       os_idrac_hostname_mapping: dict):
    """parse_jobs_metrics Parse Jobs Metrics

    Parse jobs metrics get from Slurm API

    Args:
        jobs_data (dict): Job data get from Slurm APi
        os_idrac_hostname_mapping (dict): OS-iDRAC hostname mapping

    Returns:
        list: Parsed jobs info
    """
    jobs_metrics = []

    all_jobs = jobs_data['jobs']
    attributes = ['job_id', 'array_job_id', 'array_task_id', 'name','job_state', 
                  'user_id', 'user_name', 'group_id', 'cluster', 'partition', 
                  'command', 'current_working_directory', 'batch_flag', 
                  'batch_host', 'nodes', 'node_count', 'cpus', 'tasks', 
                  'tasks_per_node', 'cpus_per_task', 'memory_per_node', 
                  'memory_per_cpu', 'priority', 'time_limit', 'deadline', 
                  'submit_time', 'preempt_time', 'suspend_time', 
                  'eligible_time', 'start_time', 'end_time', 'resize_time', 
                  'restart_cnt', 'exit_code', 'derived_exit_code']
    
    for job in all_jobs:
        nodes = job['nodes']
        hostnames = hostlist.expand_hostlist(nodes)

        # Mapping OS hostnames to iDRAC hostnames.
        if os_idrac_hostname_mapping:
            try:
                hostnames = [os_idrac_hostname_mapping[i] for i in hostnames]
            except Exception as err:
                log.error(f"Cannot mapping OS-iDRAC hostname: {err}")

        metrics = []
        for attribute in attributes:
            if attribute == 'nodes':
                metrics.append(hostnames)
            else:
                # Some attributes values are larger than 2147483647, which is 
                # not INT4, and cannot saved in TSDB
                if type(job[attribute]) is int and job[attribute] > 2147483647:
                    metrics.append(2147483647)
                else:
                    metrics.append(job[attribute])
        tuple_metrics = tuple(metrics)
        jobs_metrics.append(tuple_metrics)
            
    return jobs_metrics


def parse_node_metrics(nodes_data: dict, 
                       node_id_mapping: dict,
                       os_idrac_hostname_mapping: dict):
    """parse_node_metrics Parse Node Metircs

    Parse Nodes metrics get from Slurm API

    Args:
        nodes_data (dict): Nodes data get from Slurm APi
        node_id_mapping (dict): Node-Id mapping
        os_idrac_hostname_mapping (dict): OS-iDRAC hostname mapping

    Returns:
        dict: Parsed node metrics
    """
    all_node_metrics = {}
    state_mapping = {
        'allocated': 1,
        'idle':0,
        'down': -1
    }
    all_nodes = nodes_data['nodes']
    for node in all_nodes:
        hostname = node['hostname']

        # Mapping the OS hostname to iDRAC hostname. The hostname in 
        # node_id_mapping is using iDRAC hostname.
        if os_idrac_hostname_mapping:
            try:
                hostname = os_idrac_hostname_mapping[hostname]
            except Exception as err:
                log.error(f"Cannot map OS-hostname and IP: {err}")

        # Only process those nodes that are in node_id_mapping dict. 
        if hostname in node_id_mapping:
            node_id = node_id_mapping[hostname]
            # CPU load
            cpu_load = int(node['cpu_load'])
            # Some down nodes report cpu_load large than 2147483647, which is 
            # not INT4 and cannot saved in TSDB
            if cpu_load > 2147483647: 
                cpu_load = 2147483647
            # Memory usage
            free_memory = node['free_memory']
            real_memory = node['real_memory']
            memory_usage = ((real_memory - free_memory)/real_memory) * 100
            memory_used = real_memory - free_memory
            f_memory_usage = float("{:.2f}".format(memory_usage))
            # Status
            state = node['state']
            f_state = state_mapping[state]
            node_data = {
                'cpu_load': cpu_load,
                'memoryusage': f_memory_usage,
                'memory_used': memory_used,
                'state': f_state
            }
            all_node_metrics.update({
                node_id: node_data
            })
    return all_node_metrics


def parse_node_jobs(jobs_metrics: dict, 
                    node_id_mapping:dict,
                    os_idrac_hostname_mapping: dict):
    """parse_node_jobs Parse Node-Jobs

    Parse nodes-job correlation

    Args:
        jobs_metrics (dict): Job metrics get from Slurm APi
        node_id_mapping (dict): Node-Id mapping
        os_idrac_hostname_mapping (dict): OS-iDRAC hostname mapping

    Returns:
        dict: node-jobs correlation
    """
  
    node_jobs = {}
    all_jobs = jobs_metrics['jobs']
    # Get job-nodes correlation
    job_nodes = {}
    for job in all_jobs:
        valid_flag = True
        if job['job_state'] == "RUNNING":
            job_id = job['job_id']
            nodes = job['nodes']
            # Get node ids
            hostnames = hostlist.expand_hostlist(nodes)

            # Mapping OS hostnames to iDRAC hostnames.
            if os_idrac_hostname_mapping:
                try:
                    hostnames = [os_idrac_hostname_mapping[i] for i in hostnames]
                except Exception as err:
                    log.error(f"Cannot mapping OS-iDRAC hostname: {err}")
            
            # Check if hostname is in node_id_mapping. 
            # If not, ignore this job info.
            for hostname in hostnames:
                if hostname not in node_id_mapping:
                    valid_flag = False
                    break

            if valid_flag:
                node_ids = [node_id_mapping[i] for i in hostnames]
                node_ids.sort()
                # Get cpu counts for each node
                allocated_nodes = job['job_resources']['allocated_nodes']
                cpu_counts = [resource['cpus'] for node, resource in allocated_nodes.items()]
                job_nodes.update({
                    job_id: {
                        'nodes': node_ids,
                        'cpus': cpu_counts
                    }
                })
    # Get nodes-job correlation
    for job, nodes_cpus in job_nodes.items():
        for i, node in enumerate(nodes_cpus['nodes']):
            if node not in node_jobs:
                node_jobs.update({
                    node: {
                        'jobs':[job],
                        'cpus':[nodes_cpus['cpus'][i]]
                    }
                })
            else:
                node_jobs[node]['jobs'].append(job)
                node_jobs[node]['cpus'].append(nodes_cpus['cpus'][i])

    return node_jobs