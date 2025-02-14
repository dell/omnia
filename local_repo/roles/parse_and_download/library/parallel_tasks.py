# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

#!/usr/bin/python
 
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.process_parallel import execute_parallel, log_table_output
from ansible.module_utils.download_common import process_manifest,process_tarball,process_git,process_shell,process_ansible_galaxy_collection,process_iso,process_pip
from ansible.module_utils.download_image import process_image
from ansible.module_utils.download_rpm import process_rpm
from ansible.module_utils.standard_logger import setup_standard_logger
from prettytable import PrettyTable
from datetime import datetime
import logging
import os
import time
from ansible.module_utils.software_utils import (
    get_software_names,
    check_csv_existence,
    get_failed_software,
    process_software,
    load_json,
    load_yaml,
    get_json_file_path,
    get_csv_file_path,
    transform_package_dict,
    parse_repo_urls,
    set_version_variables,
    get_subgroup_dict
)
import json
 
def determine_function(task, repo_store_path, csv_file_path, user_data, version_variables):
    """
    Determines the appropriate function and its arguments to process a given task.
 
    Args:
        task (dict): A dictionary containing information about the task to be processed.
        repo_store_path (str): The path to the repository store.
        csv_file_path (str): The path to the CSV file.
        user_data (dict): A dictionary containing user data.
        version_variables (dict): A dictionary containing version variables.
 
    Returns:
        tuple: A tuple containing the function to process the task and its arguments.
 
    Raises:
        ValueError: If the task type is unknown.
        RuntimeError: If an error occurs while determining the function.
    """
    try:
        # Ensure the log directory exists
        os.makedirs(csv_file_path, exist_ok=True)
        cluster_os_type = user_data['cluster_os_type']
        cluster_os_version = user_data['cluster_os_version']
 
         #version_variables = {"k8s_version": "1.28.1"}
        task_type = task.get("type")
        status_file = f'{csv_file_path}/status.csv'
 
        if task_type == "manifest":
            return process_manifest, [task, repo_store_path, status_file]
        elif task_type == "git":
            return process_git, [task, repo_store_path, status_file]
        elif task_type == "tarball":
            return process_tarball, [task, repo_store_path, status_file, version_variables]
        elif task_type == "shell":
            return process_shell, [task, repo_store_path, status_file]
        elif task_type == "ansible_galaxy_collection":
            return process_ansible_galaxy_collection, [task, repo_store_path, status_file]
        elif task_type == "iso":
            return process_iso, [task, repo_store_path, status_file, cluster_os_type, cluster_os_version, version_variables]
        elif task_type == "pip_module":
            return process_pip, [task, repo_store_path, status_file]
        elif task_type == "image":
            return process_image, [task, repo_store_path, status_file, cluster_os_type, cluster_os_version, version_variables]
        elif task_type == "rpm":
            return process_rpm, [task, repo_store_path, status_file, cluster_os_type, cluster_os_version]
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    except Exception as e:
        raise RuntimeError(f"Failed to determine function for task: {str(e)}")
 
def generate_pretty_table(task_results, total_duration, overall_status):
    """
    Generates a pretty table with the task results, total duration, and overall status.
 
    Args:
        task_results (list): A list of dictionaries containing the task results.
        total_duration (str): The total duration of the tasks.
        overall_status (str): The overall status of the tasks.
 
    Returns:
        str: The pretty table as a string.
    """
   
    table = PrettyTable(["Task", "Status", "LogFile"])
    for result in task_results:
        table.add_row([result["package"], result["status"],result["logname"]])
    table.add_row(["Total Duration", total_duration,""])
    table.add_row(["Overall Status", overall_status,""])
    return table.get_string()
 
def main():
    """
    Executes a list of tasks in parallel using multiple worker processes.
 
    Args:
        tasks (list): A list of tasks (dictionaries) that need to be processed in parallel.
        nthreads (int): The number of worker processes to run in parallel.
        timeout (int): The maximum time allowed for all tasks to execute. If `None`, no timeout is enforced.
        log_dir (str): The directory where log files for the worker processes will be saved.
        log_file (str): The path to the log file for the overall task execution.
        slog_file (str): The path to the log file for the standard logger.
        csv_file_path (str): The path to a CSV file that may be needed for processing some tasks.
        repo_store_path (str): The path to the repository where task-related files are stored.
        software (list): A list of software names.
        user_json_file (str): The path to the JSON file containing user data.
 
    Returns:
        tuple: A tuple containing:
            - overall_status (str): The overall status of task execution ("SUCCESS", "FAILED", "PARTIAL", "TIMEOUT").
            - task_results_data (list): A list of dictionaries, each containing the result of an individual task.
 
    Raises:
        Exception: If an error occurs during execution.
    """
 
    module_args = dict(
        tasks=dict(type="list", required=True),
        nthreads=dict(type="int", required=False, default=4),
        timeout=dict(type="int", required=False, default=60),
        log_dir=dict(type="str", required=False, default="/tmp/thread_logs"),
        log_file=dict(type="str", required=False, default="/tmp/task_results_table.log"),
        slog_file=dict(type="str", required=False, default="/tmp/stask_results_table.log"),
        csv_file_path=dict(type="str", required=False, default="/tmp/status_results_table.csv"),
        repo_store_path=dict(type="str", required=False, default="/tmp/offline_repo"),
        software=dict(type= "list", elements='str', required=True),
        user_json_file=dict(type="str", required=False, default="")
 
    )
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
 
    tasks = module.params["tasks"]
    nthreads = module.params["nthreads"]
    log_dir = module.params["log_dir"]
    log_file = module.params["log_file"]
    slog_file = module.params["slog_file"]
    timeout = module.params["timeout"]
    csv_file_path = module.params["csv_file_path"]
    repo_store_path = module.params["repo_store_path"]
    software = module.params["software"]
    user_json_file = module.params['user_json_file']
 
    # Initialize standard logger
    slogger = setup_standard_logger(slog_file)
 
    # Initialize result dictionary
    result = dict(changed=False, task_results=[])
   
    # Record the start time of execution
    start_time = datetime.now()
    formatted_start_time = start_time.strftime("%I:%M:%S %p")  # Format as HH:MM:SS AM/PM
    slogger.info(f"Start execution time: {formatted_start_time}")
 
   
    slogger.info(f"my tasklist is {tasks}")
    slogger.info(f"Number of threads is {nthreads}")
    slogger.info(f"timeout is {timeout}")
 
    try:
        user_data = load_json(user_json_file)
        #repo_config_data = load_yaml(local_repo_config_path)
 
        cluster_os_type = user_data['cluster_os_type']
        cluster_os_version = user_data['cluster_os_version']
 
        # software_list = get_software_names(user_json_file)
 
        # Build a dictionary of software_name -> subgroup_list if exists
 
        subgroup_dict , software_names = get_subgroup_dict(user_data)
 
        version_variables = set_version_variables(user_data, software_names, cluster_os_version)
 
        #slogger.info(f"version var= {version_variables['version']}")
        slogger.info(f"cluster os is= {cluster_os_type}")
        first_entry_dict = dict([list(version_variables.items())[0]])
       
        # Execute tasks in parallel
        overall_status, task_results = execute_parallel(tasks, determine_function, nthreads, repo_store_path, csv_file_path, log_dir, user_data, first_entry_dict, slogger, timeout)
 
        # Record the end time and calculate the total duration
        end_time = datetime.now()
        formatted_end_time = end_time.strftime("%I:%M:%S %p")  # Format as HH:MM:SS AM/PM
        total_seconds = (end_time - start_time).total_seconds() # Get the total duration in seconds
       
        #minutes = int(total_seconds // 60)  # Full minutes
        #seconds = int(total_seconds % 60)  # Remaining seconds
        minutes, seconds = divmod(int(total_seconds), 60)
 
        # Format total duration properly
        if minutes > 0:
           total_duration = f"{minutes} min {seconds} sec"
        else:
           total_duration = f"{seconds} sec"
           
        #total_duration = f"{minutes} min {seconds} sec"  # Format the time string
 
        slogger.info(f"End execution time: {formatted_end_time}")
        slogger.info(f"Total execution time: {total_duration}")
 
        slogger.info(f"task_results is {task_results}")
        # Generate and log the pretty table
        table_output = generate_pretty_table(task_results, total_duration, overall_status)
        log_table_output(table_output, log_file)
 
        # Update the result dictionary with task results
        result["total_duration"] = total_duration
        result["task_results"] = task_results
        result["table_output"] = table_output
       
 
        # Determine overall status and set it in the result
        if overall_status == "SUCCESS":
            result["overall_status"] = "SUCCESS"
            result["changed"] = True
            slogger.info(f"result: {result}")
            module.exit_json(**result)
 
        elif overall_status == "PARTIAL":
            result["overall_status"] = "PARTIAL"
            module.exit_json(msg="Some tasks partially failed", **result)
 
        else:  # If overall_status is "FAILURE"
            result["overall_status"] = "FAILURE"
            module.exit_json(msg="Some tasks failed", **result)
 
    except Exception as e:
        # Ensure table output is included in the error message, even if the execution fails
        result["table_output"] = table_output if "table_output" in locals() else "No table generated."
        slogger.error(f"Execution failed: {str(e)}")
        # Fail the playbook and include the error message with the result
        module.fail_json(msg=f"Error during execution: {str(e)}", **result)
 
if __name__ == "__main__":
    main()
 
