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

"""
Ansible module for executing tasks in parallel with thread pool.

This module handles:
- Parallel execution of repository synchronization tasks
- Thread pool management with configurable concurrency
- Task result aggregation and reporting
- Error handling and timeout management
"""

#!/usr/bin/python
# pylint: disable=import-error,no-name-in-module,too-many-branches,too-many-statements,too-many-locals,too-many-return-statements,too-many-arguments,wrong-import-order,wrong-import-position,too-many-nested-blocks,unused-variable
import os
import re
from collections import defaultdict
from datetime import datetime
from prettytable import PrettyTable
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.process_parallel import execute_parallel, log_table_output
from ansible.module_utils.repo_manager.download_common import (
    build_task_repo_name,
    build_content_base_dir,
)
from ansible.module_utils.repo_manager.artifact_processor_registry import (
    get_artifact_processor,
)

DOCUMENTATION = r"""
---
module: parallel_tasks
short_description: Execute tasks in parallel with thread pool
description:
  - This module executes multiple tasks in parallel using a thread pool.
  - It is used for parallel repository synchronization and downloads.
version_added: "1.0.0"
options:
    tasks:
      description: List of tasks to execute
      required: true
      type: list
    nthreads:
      description: Maximum number of parallel workers
      required: false
      type: int
      default: 1
    dnf_max_concurrent_commands:
      description: Maximum number of RPM tasks allowed to use DNF concurrently
      required: false
      type: int
      default: 1
    timeout:
      description: Timeout per task in seconds
      required: false
      type: int
      default: 7200

author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Execute parallel sync tasks
  parallel_tasks:
    tasks: "{{ sync_tasks }}"
    nthreads: 4
    dnf_max_concurrent_commands: 1
    timeout: 7200
  register: parallel_result
"""

RETURN = r"""
results:
  description: Results from all tasks
  type: list
  returned: always
failed_tasks:
  description: List of failed tasks
  type: list
  returned: always
success_count:
  description: Number of successful tasks
  type: int
  returned: always
"""
from ansible.module_utils.repo_manager.standard_logger import setup_standard_logger
from ansible.module_utils.repo_manager.security_utils import (
    redact_sensitive_value,
    validate_no_url_credentials,
)
from ansible.module_utils.repo_manager.software_utils import (
    load_json,
    set_version_variables,
    get_subgroup_dict
)
from ansible.module_utils.repo_manager.catalog_resolver import (
    load_repo_manager_config,
    get_catalog_path,
    load_multiple_catalogs,
)
from ansible.module_utils.repo_manager.config import (
    DEFAULT_NTHREADS,
    DEFAULT_TIMEOUT,
    DNF_MAX_CONCURRENT_COMMANDS,
    LOG_DIR_DEFAULT,
    DEFAULT_LOG_FILE,
    DEFAULT_SLOG_FILE,
    CSV_FILE_PATH_DEFAULT,
    DEFAULT_REPO_STORE_PATH,
    DEFAULT_STATUS_FILENAME,
    SOFTWARE_CSV_FILENAME,
    SOFTWARE_CSV_HEADER,
    STATUS_CSV_HEADER,
    REPO_MANAGER_CONFIG_PATH_DEFAULT,
    OMNIA_CREDENTIALS_YAML_PATH,
    OMNIA_CREDENTIALS_VAULT_PATH
)


def update_status_csv(csv_dir, software, overall_status, slogger):
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
    # header = "name,status"
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
    transformed_status = re.sub(r'timeout', 'failed', transformed_status)

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


def initialize_package_status_file(csv_file_path):
    """Create or repair the package status file before workers start."""
    os.makedirs(csv_file_path, exist_ok=True)
    status_file = os.path.join(csv_file_path, DEFAULT_STATUS_FILENAME)

    if not os.path.exists(status_file) or os.stat(status_file).st_size == 0:
        with open(status_file, "w", encoding="utf-8") as file:
            file.write(STATUS_CSV_HEADER)
        return status_file

    with open(status_file, "r", encoding="utf-8") as file:
        lines = file.readlines()

    if lines and lines[0].strip() != STATUS_CSV_HEADER.strip():
        with open(status_file, "w", encoding="utf-8") as file:
            file.write(STATUS_CSV_HEADER)
            file.writelines(lines)

    return status_file


def determine_function(
    task, repo_store_path, csv_file_path, user_data, version_variables, arc,
    registry_contexts, docker_username, docker_secret_token
):
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
        cluster_os_type = user_data['cluster_os_type']
        cluster_os_version = user_data['cluster_os_version']
        repo_config_value = user_data.get("repo_config")

        # Construct the status file path using DEFAULT_STATUS_FILENAME.
        status_file = os.path.join(csv_file_path, DEFAULT_STATUS_FILENAME)

        task_type = task.get("type")

        # Build the Pulp repo name once for all non-image/non-rpm task types
        repo_name = None
        content_base_dir = None
        if task_type not in ("image", "rpm", "rpm_repo"):
            repo_name = build_task_repo_name(
                task, arc, cluster_os_type, cluster_os_version, version_variables
            )
            content_base_dir = build_content_base_dir(
                repo_store_path, arc, cluster_os_type, cluster_os_version
            )

        if task_type == "manifest":
            return get_artifact_processor(task_type), [
                task, status_file, content_base_dir, repo_name
            ]
        if task_type == "git":
            return get_artifact_processor(task_type), [
                task, status_file, content_base_dir, repo_name
            ]
        if task_type == "tarball":
            return get_artifact_processor(task_type), [
                task, status_file, version_variables,
                content_base_dir, repo_name
            ]
        if task_type == "shell":
            return get_artifact_processor(task_type), [
                task, status_file, content_base_dir, repo_name
            ]
        if task_type == "ansible_galaxy_collection":
            return get_artifact_processor(task_type), [
                task, status_file, content_base_dir, repo_name
            ]
        if task_type == "iso":
            return get_artifact_processor(task_type), [
                task, status_file, version_variables,
                content_base_dir, repo_name
            ]
        if task_type == "pip_module":
            return get_artifact_processor(task_type), [
                task, status_file, content_base_dir, repo_name,
                cluster_os_type, cluster_os_version, arc
            ]
        if task_type == "image":
            return get_artifact_processor(task_type), [
                task, status_file, version_variables, registry_contexts,
                docker_username, docker_secret_token
            ]
        if task_type == "rpm_file":
            return get_artifact_processor(task_type), [
                task, status_file, content_base_dir, repo_name
            ]
        if task_type in ("rpm", "rpm_repo"):
            return get_artifact_processor(task_type), [
                task, repo_store_path, status_file, cluster_os_type,
                cluster_os_version, repo_config_value, arc
            ]

        raise ValueError(f"Unknown task type: {task_type}")
    except Exception as error:
        raise RuntimeError(
            "Failed to determine the artifact processor for this task"
        ) from error


def generate_pretty_table(
        task_results, total_duration, overall_status, slogger,
        architecture=None, software=None):
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
        if architecture and software:
            software_label = (
                ", ".join(software)
                if isinstance(software, list) else str(software)
            )
            table.title = f"{architecture} / {software_label}"
        for result in task_results:
            # Handle missing keys gracefully
            task_data = result.get("task", {})
            package = result.get(
                "package",
                task_data.get("package", task_data.get("Name", "unknown"))
            )
            status = result.get("status", "UNKNOWN")
            logname = result.get("logname", "N/A")
            table.add_row([package, status, logname])
        table.add_row(["Total Duration", total_duration, ""])
        table.add_row(["Overall Status", overall_status, ""])
        slogger.info("Task results table generated successfully")
        return table.get_string()

    except Exception:
        slogger.error("Error occurred while generating the package-status table")
        return "Error: unable to generate the package-status table"


def generate_software_status_table(status_dict, slogger):
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

    except Exception:
        slogger.error("Error occurred while generating the software-status table")
        return "Error: unable to generate the software-status table"


def main():
    """
    Executes a list of tasks in parallel using multiple worker processes.

    Args:
        tasks (list): A list of tasks (dictionaries) that need to be processed in parallel.
        nthreads (int): The number of worker processes to run in parallel.
        timeout (int): The maximum time allowed for all tasks to execute.
                    If `None`, no timeout is enforced.
        log_dir (str): The directory where log files for the worker processes will be saved.
        log_file (str): The path to the log file for the overall task execution.
        slog_file (str): The path to the log file for the standard logger.
        csv_file_path (str): The path to a CSV file that may be needed for processing some tasks.
        repo_store_path (str): The path to the repository where task-related files are stored.
        software (list): A list of software names.
        user_json_file (str): The path to the JSON file containing user data.
        show_softwares_status (bool): Whether to display the software status;
                                optional, defaults to False.
        overall_status_dict (dict): A dictionary containing overall software status
                                information; optional, defaults to an empty dict.
            Dictionary containing software status information grouped by software names.
            Each key (e.g., 'service_k8s') maps to a list of dictionaries,
            where each dictionary contains:
                - 'arch' (str): Architecture name, e.g., 'x86_64' or 'aarch64'.
                - 'overall_status' (str): Status of the software on that architecture,
                                        e.g., 'SUCCESS'.
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
            - overall_status (str): The overall status of task execution
                                 ("SUCCESS", "FAILED", "PARTIAL", "TIMEOUT").
            - task_results_data (list): A list of dictionaries, each containing
                                    the result of an individual task.
    Raises:
        Exception: If an error occurs during execution.
    """

    module_args = {
        "tasks": {"type": "list", "required": True},
        "nthreads": {"type": "int", "required": False, "default": DEFAULT_NTHREADS},
        "dnf_max_concurrent_commands": {
            "type": "int", "required": False,
            "default": DNF_MAX_CONCURRENT_COMMANDS
        },
        "timeout": {"type": "int", "required": False, "default": DEFAULT_TIMEOUT},
        "log_dir": {"type": "str", "required": False, "default": LOG_DIR_DEFAULT},
        "log_file": {"type": "str", "required": False, "default": DEFAULT_LOG_FILE},
        "slog_file": {"type": "str", "required": False, "default": DEFAULT_SLOG_FILE},
        "csv_file_path": {"type": "str", "required": False, "default": CSV_FILE_PATH_DEFAULT},
        "repo_store_path": {"type": "str", "required": False, "default": DEFAULT_REPO_STORE_PATH},
        "software": {"type": "list", "elements": "str", "required": True},
        "user_json_file": {"type": "str", "required": False, "default": ""},
        "cluster_os_type": {"type": "str", "required": False},
        "cluster_os_version": {"type": "str", "required": False},
        "repo_config_policy": {"type": "str", "required": False, "default": "partial"},
        "show_softwares_status": {"type": "bool", "required": False, "default": False},
        "overall_status_dict": {"type": "dict", "required": True},
        "local_repo_config_path": {
            "type": "str", "required": False,
            "default": REPO_MANAGER_CONFIG_PATH_DEFAULT
        },
        "arch": {"type": "str", "required": False},
        "omnia_credentials_yaml_path": {
            "type": "str", "required": False,
            "default": OMNIA_CREDENTIALS_YAML_PATH
        },
        "omnia_credentials_vault_path": {
            "type": "str", "required": False,
            "default": OMNIA_CREDENTIALS_VAULT_PATH
        }
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    tasks = module.params["tasks"]
    try:
        validate_no_url_credentials(tasks)
    except ValueError:
        module.fail_json(msg="Task list contains a credential-bearing URL.")
    nthreads = module.params["nthreads"]
    dnf_max_concurrent_commands = module.params["dnf_max_concurrent_commands"]
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
    slogger.info("Task list: %s", redact_sensitive_value(tasks))
    slogger.info(f"Number of threads: {nthreads}")
    slogger.info(
        "Maximum concurrent DNF commands: %d", dnf_max_concurrent_commands
    )
    slogger.info(f"Timeout: {timeout}")
    slogger.info(f"overall_status_dict: {overall_status_dict}")
    slogger.info(f"show_softwares_status: {show_softwares_status}")

    # Check if the flag to show software status is enabled
    if show_softwares_status:
        # Generate a formatted status table from the overall_status_dict parameter
        status_table = generate_software_status_table(overall_status_dict, slogger)
        module.exit_json(changed=False, msg=status_table)

    if not 1 <= nthreads <= 5:
        module.fail_json(msg="nthreads must be between 1 and 5")
    if not 1 <= dnf_max_concurrent_commands <= 5:
        module.fail_json(msg="dnf_max_concurrent_commands must be between 1 and 5")

    try:
        # Build user_data from catalog config and module params.
        cluster_os_type = module.params.get("cluster_os_type")
        cluster_os_version = module.params.get("cluster_os_version")
        repo_config_policy = module.params.get("repo_config_policy", "partial")

        if not cluster_os_type or not cluster_os_version or not arc:
            module.fail_json(
                msg=(
                    "cluster_os_type, cluster_os_version and arch are required "
                    "for package execution"
                )
            )

        if user_json_file and os.path.isfile(user_json_file):
            user_data = load_json(user_json_file)
            cluster_os_type = user_data.get('cluster_os_type', cluster_os_type)
            cluster_os_version = user_data.get('cluster_os_version', cluster_os_version)
        else:
            # Build minimal user_data from catalog config for downstream consumers
            user_data = {
                "cluster_os_type": cluster_os_type,
                "cluster_os_version": cluster_os_version,
                "repo_config": repo_config_policy,
                "softwares": [],
            }
            # Try to enrich user_data from catalog if available
            try:
                config_dir = os.path.dirname(os.path.abspath(local_repo_config_path))
                config_data, _ = load_repo_manager_config(local_repo_config_path, slogger)
                catalog_path = get_catalog_path(config_data, config_dir, slogger)
                catalogs = load_multiple_catalogs(catalog_path, slogger)
                # Build softwares list from catalog Groups for version variable extraction
                for catalog in catalogs:
                    for group_name, group_def in catalog.get("groups", {}).items():
                        sw_entry = {"name": group_name, "arch": [arc]}
                        # Extract version if available in group definition
                        if isinstance(group_def, dict) and group_def.get("version"):
                            sw_entry["version"] = group_def["version"]
                        user_data["softwares"].append(sw_entry)
            except Exception:
                slogger.warning("Could not load catalog for version variables.")

        _, software_names = get_subgroup_dict(user_data, slogger)
        version_variables = set_version_variables(
            user_data, software_names, cluster_os_version, slogger
        )
        slogger.info(f"Cluster OS: {cluster_os_type}")
        slogger.info(f"Version Variables: {version_variables}")
        # gen_result = {}
        # if not os.path.isfile(user_reg_key_path):
        #     gen_result = generate_vault_key(user_reg_key_path)
        # if gen_result is None:
        #     module.fail_json(
        #         msg=f"Unable to generate local_repo key at path: {user_reg_key_path}"
        #     )

        initialize_package_status_file(csv_file_path)

        overall_status, task_results = execute_parallel(
            tasks, determine_function, nthreads, repo_store_path, csv_file_path,
            log_dir, user_data, version_variables, arc, slogger,
            local_repo_config_path, omnia_credentials_yaml_path,
            omnia_credentials_vault_path, timeout,
            dnf_max_concurrent_commands=dnf_max_concurrent_commands
        )

        # if not is_encrypted(user_reg_cred_input):
        #     process_file(user_reg_cred_input, user_reg_key_path, 'encrypt')

        end_time = datetime.now()
        formatted_end_time = end_time.strftime("%I:%M:%S %p")
        total_seconds = (end_time - start_time).total_seconds()
        minutes, seconds = divmod(int(total_seconds), 60)
        total_duration = f"{minutes} min {seconds} sec" if minutes > 0 else f"{seconds} sec"

        slogger.info(f"End execution time: {formatted_end_time}")
        slogger.info(f"Total execution time: {total_duration}")
        slogger.info("Task results: %s", redact_sensitive_value(task_results))

        table_output = generate_pretty_table(
            task_results, total_duration, overall_status, slogger,
            architecture=arc, software=software
        )
        log_table_output(table_output, log_file)
        result["total_duration"] = total_duration
        result["task_results"] = task_results
        result["table_output"] = table_output
        result["arch"] = arc

        update_status_csv(csv_file_path, software, overall_status, slogger)

        if overall_status == "SUCCESS":
            result["overall_status"] = "SUCCESS"
            result["changed"] = True
            slogger.info("Result: %s", redact_sensitive_value(result))
            module.exit_json(**result)
        elif overall_status == "PARTIAL":
            result["overall_status"] = "PARTIAL"
            module.exit_json(msg="Some tasks partially failed", **result)
        else:
            result["overall_status"] = "FAILURE"
            module.exit_json(msg="Some tasks failed", **result)

    except RuntimeError:
        slogger.error("Repo Manager task execution failed.")
        module.fail_json(msg="Error during task execution.", **result)

    except Exception:
        result["table_output"] = (
            table_output if "table_output" in locals() else "No table generated."
        )
        slogger.error("Repo Manager task execution failed.")
        module.fail_json(msg="Error during task execution.", **result)


if __name__ == "__main__":
    main()
