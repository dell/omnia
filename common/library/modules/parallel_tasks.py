# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
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
# pylint: disable=import-error,no-name-in-module
import os
import re
from datetime import datetime
from prettytable import PrettyTable
from collections import defaultdict
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.process_parallel import execute_parallel, log_table_output
from ansible.module_utils.local_repo.download_common import (
    process_manifest,
    process_tarball,
    process_git,
    process_shell,
    process_ansible_galaxy_collection,
    process_iso,
    process_pip,
    process_rpm_file
)
from ansible.module_utils.local_repo.download_image import process_image
from ansible.module_utils.local_repo.download_rpm import process_rpm
from ansible.module_utils.local_repo.standard_logger import setup_standard_logger
from ansible.module_utils.local_repo.common_functions import generate_vault_key, process_file, is_encrypted
from ansible.module_utils.local_repo.software_utils import (
    load_json,
    set_version_variables,
    get_subgroup_dict
)
from ansible.module_utils.local_repo.config import (
    DEFAULT_NTHREADS,
    DEFAULT_TIMEOUT,
    LOG_DIR_DEFAULT,
    DEFAULT_LOG_FILE,
    DEFAULT_SLOG_FILE,
    CSV_FILE_PATH_DEFAULT,
    DEFAULT_REPO_STORE_PATH,
    USER_JSON_FILE_DEFAULT,
    DEFAULT_STATUS_FILENAME,
    SOFTWARE_CSV_FILENAME,
    SOFTWARE_CSV_HEADER,
    STATUS_CSV_HEADER,
    LOCAL_REPO_CONFIG_PATH_DEFAULT,
    OMNIA_CREDENTIALS_YAML_PATH,
    OMNIA_CREDENTIALS_VAULT_PATH
)

def update_status_csv(csv_dir, software, overall_status,slogger):
    """
    Update the status CSV file with the status for given software.

    If the software already exists, update its status.
    If 'software' is a list, update each software with the same overall_status.

    Args:
        csv_dir (str): Directory path where the CSV file resides.
        software (str or list): Software name(s) to update.
        overall_status (str): The overall status to record.
        slogger (logging.Logger): Logger instance for structured logging.
    """

    slogger.info("Starting CSV status update process")
    parent_dir = os.path.dirname(csv_dir)
    status_file = os.path.join(parent_dir, SOFTWARE_CSV_FILENAME)
    #header = "name,status"
    header = SOFTWARE_CSV_HEADER

    # Create the file with header if it does not exist.
    if not os.path.exists(status_file):
        slogger.info("Status file not found. Creating new file with header.")
        with open(status_file, "w", encoding="utf-8") as f:
            f.write(header + "\n")

    # Read the existing file content.
    slogger.info("Reading existing CSV content")
    with open(status_file, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    # Ensure there is a header.
    if not lines or lines[0] != header:
        lines.insert(0, header)

    # Build a dictionary for existing entries (skip header).
    status_dict = {}
    for line in lines[1:]:
        parts = line.split(',')
        if len(parts) >= 2:
            key = parts[0].strip()
            value = parts[1].strip()
            status_dict[key] = value

    # Transform the new status.
    transformed_status = re.sub(r'failure', 'failed', overall_status.lower())
    transformed_status = re.sub(r'partial', 'failed', overall_status.lower())

    # Update or add the entry for each given software.
    if isinstance(software, list):
        for sw in software:
            status_dict[sw] = transformed_status
    else:
        status_dict[software] = transformed_status

    # Recreate the CSV content.
    final_lines = [header]
    for key, value in status_dict.items():
        final_lines.append(f"{key},{value}")

    # Write the updated content back to the file.
    with open(status_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))

    slogger.info(f"Successfully updated status CSV at {status_file}")


def determine_function(task, repo_store_path, csv_file_path, user_data, version_variables, arc, user_registries, docker_username, docker_password):
    """
    Determines the appropriate function and its arguments to process a given task.

    Args:
        task (dict): A dictionary containing information about the task to be processed.
        repo_store_path (str): The path to the repository store.
        csv_file_path (str): The path to the CSV file.
        user_data (dict): A dictionary containing user data.
        version_variables (dict): A dictionary containing version variables.
        arc (str): Architecture of package to be downloaded

    Returns:
        tuple: A tuple containing the function to process the task and its arguments.

    Raises:
        ValueError: If the task type is unknown.
        RuntimeError: If an error occurs while determining the function.
    """
    try:
        # Ensure the CSV directory exists.
        os.makedirs(csv_file_path, exist_ok=True)
        cluster_os_type = user_data['cluster_os_type']
        cluster_os_version = user_data['cluster_os_version']
        repo_config_value = user_data.get("repo_config")

        # Construct the status file path using DEFAULT_STATUS_FILENAME.
        status_file = os.path.join(csv_file_path, DEFAULT_STATUS_FILENAME)
        if not os.path.exists(status_file) or os.stat(status_file).st_size == 0:
            with open(status_file, 'w', encoding="utf-8") as file:
                file.write(STATUS_CSV_HEADER)


        task_type = task.get("type")
        if task_type == "manifest":
            return process_manifest, [task, repo_store_path, status_file, cluster_os_type, cluster_os_version, arc]
        if task_type == "git":
            return process_git, [task, repo_store_path, status_file, cluster_os_type, cluster_os_version, arc]
        if task_type == "tarball":
            return process_tarball, [task, repo_store_path, status_file, version_variables, cluster_os_type, cluster_os_version, arc]
        if task_type == "shell":
            return process_shell, [task, repo_store_path, status_file, cluster_os_type, cluster_os_version, arc]
        if task_type == "ansible_galaxy_collection":
            return process_ansible_galaxy_collection, [task, repo_store_path, status_file, cluster_os_type, cluster_os_version, arc]
        if task_type == "iso":
            return process_iso, [task, repo_store_path, status_file,
                                 cluster_os_type, cluster_os_version, version_variables, arc]
        if task_type == "pip_module":
            return process_pip, [task, repo_store_path, status_file, cluster_os_type, cluster_os_version, arc]
        if task_type == "image":
            return process_image, [task, status_file, version_variables, user_registries, docker_username, docker_password]
        if task_type == "rpm_file":
            return process_rpm_file, [task, repo_store_path, status_file, cluster_os_type, cluster_os_version, arc]
        if task_type == "rpm":
            return process_rpm, [task, repo_store_path, status_file,
                                 cluster_os_type, cluster_os_version, repo_config_value, arc]

        raise ValueError(f"Unknown task type: {task_type}")
    except Exception as e:
        raise RuntimeError(f"Failed to determine function for task: {str(e)}")


def generate_pretty_table(task_results, total_duration, overall_status,slogger):
    """
    Generates a pretty table with the task results, total duration, and overall status.

    Args:
        task_results (list): A list of dictionaries containing the task results.
        total_duration (str): The total duration of the tasks.
        overall_status (str): The overall status of the tasks.
        slogger (logging.Logger): Logger instance for structured logging.

    Returns:
        str: The pretty table as a string.
    """
    try:
        slogger.info("Starting generation of task results pretty table")

        if not task_results or not isinstance(task_results, list):
            slogger.error("Invalid or empty task_results provided")
            return "No task results available."

        slogger.info(f"Received {len(task_results)} task results for table generation")

        table = PrettyTable(["Task", "Status", "LogFile"])
        for result in task_results:
            table.add_row([result["package"], result["status"], result["logname"]])
        table.add_row(["Total Duration", total_duration, ""])
        table.add_row(["Overall Status", overall_status, ""])
        return table.get_string()

        slogger.info("Task results table generated successfully")

    except Exception as e:
        slogger.error(f"Error occurred while generating pretty table: {e}")
        return f"Error: {e}"

def generate_software_status_table(status_dict,slogger):
    """
    Returns status tables of software grouped by architecture.

    Args:
        status_dict (dict): Software info with 'arch' and 'overall_status' for each entry.
        slogger (logging.Logger): Logger instance for structured logging.

    Returns:
        str: Formatted tables (per arch) showing software name and status.
    """
    try:
        slogger.info("Starting generation of software status table")
        grouped = defaultdict(list)

        # status_dict is expected to have software names as keys, list of dicts as values
        slogger.info("Grouping software entries by architecture")
        for software_name, entries in status_dict.items():
            for info in entries:
                arch = info.get("arch", "unknown")
                status = info.get("overall_status", "unknown")
                grouped[arch].append((software_name, status))

        # Build tables for each arch
        tables = []
        for arch, items in grouped.items():
            slogger.info(f"Creating table for architecture: {arch}")
            table = PrettyTable()
            table.title = f"{arch} Software Stack Download Overview"
            table.field_names = ["Name", "Status"]
            for name, status in items:
                table.add_row([name, status.lower()])

            tables.append(table.get_string())
            slogger.info(f"Completed table for {arch}")

        slogger.info("Software status table generation completed successfully")
        return "\n\n".join(tables)

    except Exception as e:
        slogger.error(f"Error occurred while generating software status table: {e}")
        return f"Error: {e}"

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
        user_json_file (str): The path to the JSON file containing use
        show_softwares_status (bool): Whether to display the software status; optional, defaults to False.  
        overall_status_dict (dict): A list containing overall software status information; optional, defaults to an empty dict.
          Dictionary containing software status information grouped by software names.  
          Each key (e.g., 'service_k8s') maps to a list of dictionaries,  
          where each dictionary contains:
              - 'arch' (str): Architecture name, e.g., 'x86_64' or 'aarch64'.  
              - 'overall_status' (str): Status of the software on that architecture, e.g., 'SUCCESS'.  
          Example:
              {
                  "service_k8s": [
                      {"arch": "x86_64", "overall_status": "SUCCESS"},
                      {"arch": "aarch64", "overall_status": "SUCCESS"}
                  ]
              }
          Defaults to an empty dict if not provided.

    Returns:
        tuple: A tuple containing:
            - overall_status (str): The overall status of task execution ("SUCCESS", "FAILED", "PARTIAL", "TIMEOUT").
            - task_results_data (list): A list of dictionaries, each containing the result of an individual task.
    Raises:
        Exception: If an error occurs during execution.
    """
    # module_args = {
    #     "tasks": {"type": "list", "required": True},
    #     "nthreads": {"type": "int", "required": False, "default": DEFAULT_NTHREADS},
    #     "timeout": {"type": "int", "required": False, "default": DEFAULT_TIMEOUT},
    #     "log_dir": {"type": "str", "required": False, "default": LOG_DIR_DEFAULT},
    #     "log_file": {"type": "str", "required": False, "default": DEFAULT_LOG_FILE},
    #     "slog_file": {"type": "str", "required": False, "default": DEFAULT_SLOG_FILE},
    #     "csv_file_path": {"type": "str", "required": False, "default": CSV_FILE_PATH_DEFAULT},
    #     "repo_store_path": {"type": "str", "required": False, "default": DEFAULT_REPO_STORE_PATH},
    #     "software": {"type": "list", "elements": "str", "required": True},
    #     "user_json_file": {"type": "str", "required": False, "default": USER_JSON_FILE_DEFAULT},
    #     "show_softwares_status": {"type": "bool", "required": False, "default": False},
    #     "overall_status_dict": {"type": "dict","required": True},
    #     "local_repo_config_path": {"type": "str", "required": False, "default": LOCAL_REPO_CONFIG_PATH_DEFAULT},
    #     "arch": {"type": "str", "required": False},
    #     "user_reg_cred_input": {"type": "str", "required": False, "default": USER_REG_CRED_INPUT},
    #     "user_reg_key_path": {"type": "str", "required": False, "default": USER_REG_KEY_PATH},
    #     "omnia_credentials_yaml_path": {"type": "str", "required": False, "default": OMNIA_CREDENTIALS_YAML_PATH},
    #     "omnia_credentials_vault_path": {"type": "str", "required": False, "default": OMNIA_CREDENTIALS_VAULT_PATH}
    # }

    module_args = {
        "tasks": {"type": "list", "required": True},
        "nthreads": {"type": "int", "required": False, "default": DEFAULT_NTHREADS},
        "timeout": {"type": "int", "required": False, "default": DEFAULT_TIMEOUT},
        "log_dir": {"type": "str", "required": False, "default": LOG_DIR_DEFAULT},
        "log_file": {"type": "str", "required": False, "default": DEFAULT_LOG_FILE},
        "slog_file": {"type": "str", "required": False, "default": DEFAULT_SLOG_FILE},
        "csv_file_path": {"type": "str", "required": False, "default": CSV_FILE_PATH_DEFAULT},
        "repo_store_path": {"type": "str", "required": False, "default": DEFAULT_REPO_STORE_PATH},
        "software": {"type": "list", "elements": "str", "required": True},
        "user_json_file": {"type": "str", "required": False, "default": USER_JSON_FILE_DEFAULT},
        "show_softwares_status": {"type": "bool", "required": False, "default": False},
        "overall_status_dict": {"type": "dict","required": True},
        "local_repo_config_path": {"type": "str", "required": False, "default": LOCAL_REPO_CONFIG_PATH_DEFAULT},
        "arch": {"type": "str", "required": False},
        "omnia_credentials_yaml_path": {"type": "str", "required": False, "default": OMNIA_CREDENTIALS_YAML_PATH},
        "omnia_credentials_vault_path": {"type": "str", "required": False, "default": OMNIA_CREDENTIALS_VAULT_PATH}
    }
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
    user_json_file = module.params["user_json_file"]
    show_softwares_status = module.params["show_softwares_status"]
    overall_status_dict = module.params["overall_status_dict"]
    local_repo_config_path = module.params["local_repo_config_path"]
    arc = module.params["arch"]
    # user_reg_cred_input = module.params["user_reg_cred_input"]
    # user_reg_key_path = module.params["user_reg_key_path"]
    omnia_credentials_yaml_path = module.params["omnia_credentials_yaml_path"]
    omnia_credentials_vault_path = module.params["omnia_credentials_vault_path"]

    # Initialize standard logger.
    slogger = setup_standard_logger(slog_file)
    result = {"changed": False, "task_results": []}
    # Record start time.
    start_time = datetime.now()
    formatted_start_time = start_time.strftime("%I:%M:%S %p")
    slogger.info(f"Start execution time: {formatted_start_time}")
    slogger.info(f"Task list: {tasks}")
    slogger.info(f"Number of threads: {nthreads}")
    slogger.info(f"Timeout: {timeout}")
    slogger.info(f"overall_status_dict: {overall_status_dict}")
    slogger.info(f"show_softwares_status: {show_softwares_status}")

    # Check if the flag to show software status is enabled
    if show_softwares_status:
        # Generate a formatted status table from the overall_status_dict parameter
        status_table = generate_software_status_table(overall_status_dict,slogger)
        module.exit_json(changed=False, msg=status_table)

    try:
        user_data = load_json(user_json_file)
        cluster_os_type = user_data['cluster_os_type']
        cluster_os_version = user_data['cluster_os_version']

        subgroup_dict, software_names = get_subgroup_dict(user_data,slogger)
        version_variables = set_version_variables(user_data, software_names, cluster_os_version,slogger)
        slogger.info(f"Cluster OS: {cluster_os_type}")
        slogger.info(f"Version Variables: {version_variables}")
        # gen_result = {}
        # if not os.path.isfile(user_reg_key_path):
        #     gen_result = generate_vault_key(user_reg_key_path)
        # if gen_result is None:
        #     module.fail_json(msg=f"Unable to generate local_repo key at path: {user_reg_key_path}")

        overall_status, task_results = execute_parallel(
            tasks, determine_function, nthreads, repo_store_path, csv_file_path,
            log_dir, user_data, version_variables, arc, slogger, local_repo_config_path,
            omnia_credentials_yaml_path, omnia_credentials_vault_path, timeout
        )

        # if not is_encrypted(user_reg_cred_input):
        #     process_file(user_reg_cred_input,user_reg_key_path,'encrypt')

        end_time = datetime.now()
        formatted_end_time = end_time.strftime("%I:%M:%S %p")
        total_seconds = (end_time - start_time).total_seconds()
        minutes, seconds = divmod(int(total_seconds), 60)
        total_duration = f"{minutes} min {seconds} sec" if minutes > 0 else f"{seconds} sec"

        slogger.info(f"End execution time: {formatted_end_time}")
        slogger.info(f"Total execution time: {total_duration}")
        slogger.info(f"Task results: {task_results}")

        table_output = generate_pretty_table(task_results, total_duration, overall_status,slogger)
        log_table_output(table_output, log_file)
        result["total_duration"] = total_duration
        result["task_results"] = task_results
        result["table_output"] = table_output
        result["arch"] = arc

        update_status_csv(csv_file_path, software, overall_status, slogger)

        if overall_status == "SUCCESS":
            result["overall_status"] = "SUCCESS"
            result["changed"] = True
            slogger.info(f"Result: {result}")
            module.exit_json(**result)
        elif overall_status == "PARTIAL":
            result["overall_status"] = "PARTIAL"
            module.exit_json(msg="Some tasks partially failed", **result)
        else:
            result["overall_status"] = "FAILURE"
            module.exit_json(msg="Some tasks failed", **result)

    except RuntimeError as e:
        slogger.error(f"Execution failed: {str(e)}")
        module.fail_json(msg=f"Error during execution: {str(e)}", **result)


    except Exception as e:
        result["table_output"] = table_output if "table_output" in locals() else "No table generated."
        slogger.error(f"Execution failed: {str(e)}")
        module.fail_json(msg=f"Error during execution: {str(e)}", **result)

if __name__ == "__main__":
    main()
