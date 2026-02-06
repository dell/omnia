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
# pylint: disable=import-error,no-name-in-module,too-many-positional-arguments,too-many-locals,too-many-arguments
"""This module handles parallel processing tasks for local repository."""

import os
import logging
import multiprocessing
import subprocess
import time
import threading
import traceback
import json
import yaml
import json
import requests
from jinja2 import Template
from ansible.module_utils.local_repo.common_functions import (
    load_yaml_file,
    is_encrypted,
    process_file
)
from ansible.module_utils.local_repo.config import (
    OMNIA_CREDENTIALS_YAML_PATH,
    OMNIA_CREDENTIALS_VAULT_PATH,
    # USER_REG_CRED_INPUT,
    # USER_REG_KEY_PATH
)
# Global lock for logging synchronization
log_lock = multiprocessing.Lock()

def load_docker_credentials(vault_yml_path, vault_password_file):
    """
    Decrypts an Ansible Vault YAML file, extracts docker_username and docker_password,
    and validates them using Docker Hub API.

    Validation Logic:
        - Validates credentials via Docker Hub REST API
        - Returns credentials if authentication succeeds (HTTP 200)
        - Raises RuntimeError for all authentication failures

    Args:
        vault_yml_path (str): Path to the encrypted Ansible Vault YAML file.
        vault_password_file (str): Path to the vault password file.

    Returns:
        tuple: (docker_username, docker_password) or (None, None) if not provided.

    Raises:
        RuntimeError: If vault decryption fails, YAML parsing fails, Docker Hub API 
                     authentication fails, network errors occur, or requests module 
                     is not installed.
    """
    try:
        env = os.environ.copy()
        env["ANSIBLE_VAULT_PASSWORD_FILE"] = vault_password_file

        result = subprocess.run(
            ["ansible-vault", "view", vault_yml_path],
            capture_output=True,
            text=True,
            check=True,
            env=env
        )
        data = yaml.safe_load(result.stdout)
        docker_username = data.get("docker_username")
        docker_password = data.get("docker_password")

        # If either credential is missing, skip validation
        if not docker_username or not docker_password:
            return None, None

        # Validate credentials using Docker Hub API
        try:
            payload = json.dumps({"username": docker_username, "password": docker_password})
            response = requests.post(
                "https://hub.docker.com/v2/users/login/",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "curl/8.0"
                },
                timeout=30
            )

            if response.status_code == 200:
                return docker_username, docker_password
            
            if response.status_code == 429:
                raise RuntimeError("Docker Hub rate limit exceeded. Please try again later.")

            # Handle authentication failures
            if response.status_code == 401:
                raise RuntimeError("Invalid Docker Hub username or password.")

            # Handle malformed client request
            if response.status_code == 400:
                raise RuntimeError("Bad request sent to Docker Hub. Check username/password format.")

            # Handle server-side errors (5xx)
            if 500 <= response.status_code < 600:
                raise RuntimeError(
                    f"Docker Hub server error (status {response.status_code}). Try again later."
                )

            # Catch-all for other unexpected statuses
            raise RuntimeError(
                f"Docker Hub authentication failed with unexpected status {response.status_code}."
            )

        except requests.RequestException as error:
            raise RuntimeError(
                "Unable to reach Docker Hub (network DNS/timeout/SSL issue)."
            ) from error

    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"Vault decryption failed: {error.stderr.strip()}") from error
    except yaml.YAMLError as error:
        raise RuntimeError(f"Failed to parse decrypted YAML: {error}") from error

def log_table_output(table_output, log_file):
    """
    Writes the provided table output to a log file.
    Args:
        table_output (str): The table output to be written to the log file.
        log_file (str): The path of the log file where the table output should be written.
    Raises:
        RuntimeError: If there is an error during the file writing process or directory creation.
    """
    try:
        # Ensure the directory for the log file exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        # Write the table output to the log file
        with open(log_file, "w") as file:
            file.write("Command Execution Results Table:\n")  # Add a header to the table
            file.write(table_output)  # Write the actual table content
    except Exception as e:
        # If there is an error, raise a RuntimeError with the error message
        raise RuntimeError(f"Failed to write table output to log file: {str(e)}")

def setup_logger(log_dir,log_file_path):
    """
    Sets up and configures a logger to write logs to a specified file.
    Args:
        log_file_path (str): The path where the log file will be saved.
    Returns:
        logging.Logger: The configured logger instance.
    """
    # Ensure the log directory exists
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(log_file_path)  # Create a logger with the provided log file path
    logger.setLevel(logging.INFO)  # Set the log level to INFO
    # Check if the logger already has handlers to avoid duplicate log entries
    if not logger.hasHandlers():
        # Create a file handler to write logs to the specified file
        file_handler = logging.FileHandler(log_file_path)
        # Define the format for log messages
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # Apply the formatter to the file handler
        file_handler.setFormatter(formatter)
        # Add the file handler to the logger
        logger.addHandler(file_handler)
    return logger

def execute_task(task, determine_function, user_data, version_variables, arc,
                repo_store_path, csv_file_path,logger, user_registries,
                docker_username, docker_password, timeout=None):
    """
    Executes a task by determining the appropriate function to call, managing execution time, 
    handling timeouts, and logging the results.

    Args:
        task (dict): The task to execute, expected to contain necessary details such as "package".
        determine_function (function): A function that takes a task, repo_store_path,
                                       and csv_file_path and returns the function to
                                       call and its arguments.
        arc (str): Architecture of package to be downloaded
        repo_store_path (str): The path to the repository where files are stored.
        csv_file_path (str): Path to a CSV file to be processed as part of the task.
        logger (logging.Logger): The logger instance for logging the task's execution.
        timeout (float, optional): The maximum time allowed for the task to execute.
        user_registries (str): List of user registries 

    Returns:
        dict: A dictionary containing the task information, its execution status,
              any output, and any errors.
    """
    try:
        start_time = time.time()  # Track the start time of the task execution
        with log_lock:
            logger.info(f"### {execute_task.__name__} start ###")  # Log task start

        # Determine the function and its arguments using the provided `determine_function`
        function, args = determine_function(task, repo_store_path, csv_file_path, user_data,
                         version_variables, arc, user_registries, docker_username, docker_password)

        while True:
            elapsed_time = time.time() - start_time  # Calculate elapsed time
            logger.info(f"--->{elapsed_time:.2f}s.")  # Log the elapsed time

            # Check if the timeout has been reached
            if timeout and elapsed_time > timeout:
                with log_lock:
                    logger.info(
                      f"Timeout reached ({elapsed_time:.2f}s), stopping task execution for {task}."
                    )
                return {
                    "task": task,
                    "package": task.get("package", ""),  # Extract package name if available
                    "status": "TIMEOUT",
                    "output": "",
                    "error": f"Timeout reached after {elapsed_time:.2f}s"
                }

            # Execute the task and get the result
            result = function(*args, logger=logger)

            # If the function has completed successfully, break out of the loop
            if result:
                break

            # If the task hasn't finished yet, wait before retrying
            time.sleep(0.1)

        # Log the success and return the result
        with log_lock:
            logger.info(f"Task {function.__name__} succeeded.")
            logger.info(f"### {execute_task.__name__} end ###")

        return {
            "task": task,
            "package": task.get("package", ""),  
            "status": result.upper(),  
            "output": result,
            "error": ""
        }
    except Exception as e:
        # Log the error if the task fails
        with log_lock:
            logger.error(f"Task failed: {str(e)}")
        return {
            "task": task,
            "package": task.get("package", ""),  
            "status": "FAILED",  
            "output": "",
            "error": str(e)  # Include the error message
        }

def worker_process(task, determine_function, user_data, version_variables, arc, repo_store_path,
                  csv_file_path, log_dir, result_queue, user_registries,
                  docker_username, docker_password, timeout):
    """
    Executes a task in a separate worker process, logs the process execution,
    and puts the result in a result queue.
    Args:
        task (dict): The task to be processed, containing details like the package to be processed.
        determine_function (function): A function that determines the function to call
        and its arguments for the task.
        user_data: content from software_config.json
        version_variables: softwarename_version for versioned softwares
        arc: Architecture of software
        repo_store_path (str): Path to the repository where task-related files are stored.
        csv_file_path (str): Path to a CSV file that may be needed for processing the task.
        log_dir (str): Directory where log files for the worker process should be saved.
        result_queue (multiprocessing.Queue): Queue for putting the result of the 
        task execution (used for inter-process communication).
        docker_username: Docker username provided by the user
        docker_password: Docker password for the provided username
        user_registries (str): List of user registries
        timeout (float): The maximum allowed time for the task execution.
    Returns:
        None: The result is placed into the `result_queue`, so no return value is needed.
    """
    #Define the log file path using process ID for uniqueness
    thread_log_path = os.path.join(log_dir, f"package_status_{os.getpid()}.log")
    # Setup logger specific to this worker process
    logger = setup_logger(log_dir,thread_log_path)
    try:
        # Log the start of the worker process execution
        with log_lock:
            logger.info(f"Worker process {os.getpid()} started  execution.")
        # Execute the task by calling the `execute_task` function and passing necessary arguments
        result = execute_task(task, determine_function, user_data, version_variables, arc,
                             repo_store_path, csv_file_path, logger, user_registries,
                             docker_username, docker_password, timeout)
        result["logname"] = f"package_status_{os.getpid()}.log"
        # Put the result of the task execution into the result_queue for further processing
        result_queue.put(result)
        # Log the successful completion of the task execution
        with log_lock:
            logger.info(f"Worker process {os.getpid()} completed task execution.")
    except Exception as e:
        # Log any errors encountered during task execution
        with log_lock:
            logger.error("Worker process %s encountered an internal error.", os.getpid())
        # If an error occurs, put a failure result in the queue indicating task failure
        # Return a safe, generic error message to caller
        safe_error_message = "Task execution failed due to an internal error."
        result_queue.put({"task": task, "status": "FAILED", "output": "", "error": safe_error_message })

def execute_parallel(
    tasks,
    determine_function,
    nthreads,
    repo_store_path,
    csv_file_path,
    log_dir,
    user_data,
    version_variables,
    arc,
    standard_logger,
    local_repo_config_path,
    # user_reg_cred_input,
    # user_reg_key_path,
    omnia_credentials_yaml_path,
    omnia_credentials_vault_path,
    timeout
):
    """
    Executes a list of tasks in parallel using multiple worker processes.
    Args:
        tasks (list): A list of tasks (dictionaries) that need to be processed in parallel.
        determine_function (function): A function that determines which function to 
        execute and its arguments for each task.
        nthreads (int): The number of worker processes to run in parallel.
        repo_store_path (str): Path to the repository where task-related files are stored.
        csv_file_path (str): Path to a CSV file that may be needed for processing some tasks.
        log_dir (str): Directory where log files for the worker processes will be saved.
        standard_logger (logging.Logger): A shared logger for overall task execution.
        timeout (float, optional): The maximum time allowed for all tasks to execute.
        If `None`, no timeout is enforced.
        local_repo_config_path (str): Path for local_repo_config.yml
    Returns:
        tuple: A tuple containing:
            - overall_status (str): The overall status of task 
              execution ("SUCCESS", "FAILED", "PARTIAL", "TIMEOUT").
            - task_results_data (list): A list of dictionaries,
              each containing the result of an individual task.
    """
    # Create a shared queue for collecting task results from worker processes
    result_queue = multiprocessing.Manager().Queue()
    with log_lock:
        standard_logger.info("Starting parallel task execution.")

    config = load_yaml_file(local_repo_config_path)
    user_registries = config.get("user_registry", [])
    # if user_registries:
    #     if is_encrypted(user_reg_cred_input):
    #         process_file(user_reg_cred_input, user_reg_key_path, 'decrypt')

    #     file2_data = load_yaml_file(user_reg_cred_input)
    #     cred_lookup = {
    #         entry['name']: entry
    #         for entry in file2_data.get('user_registry_credential', [])
    #     }
    #     # Update user_registry entries with credentials if required
    #     for registry in user_registries:
    #         if registry.get("requires_auth"):
    #             creds = cred_lookup.get(registry.get("name"))
    #             if creds:
    #                 registry["username"] = creds.get("username")
    #                 registry["password"] = creds.get("password")


    try:
        docker_username, docker_password = load_docker_credentials(omnia_credentials_yaml_path,
                                                                  omnia_credentials_vault_path)
    except RuntimeError as e:
        raise
    # Create a pool of worker processes to handle the tasks
    with multiprocessing.Pool(processes=nthreads) as pool:
        task_results = []  # List to hold references to the async results of the tasks

        # Submit each task to the pool for parallel execution
        for task in tasks:
            package_template = Template(task.get('package', None))
            package_name = package_template.render(**version_variables)
            task['package'] = package_name
            task_results.append(pool.apply_async(worker_process, (task, determine_function, user_data,
                               version_variables, arc, repo_store_path, csv_file_path, log_dir, result_queue,
                               user_registries,docker_username, docker_password, timeout)))

        pool.close()  # Close the pool to new tasks once all have been submitted
        start_time = time.time()  # Start time for overall task execution
        tasks_are_not_completed = False
        # Check the status of the tasks periodically and enforce the timeout if necessary
        while task_results:
            elapsed_time = time.time() - start_time  # Calculate elapsed time
            if timeout and elapsed_time > timeout:  # Check if overall timeout has been reached
                with log_lock:
                    standard_logger.warning(
                       f"Overall timeout reached ({elapsed_time:.2f}s), stopping remaining tasks."
                )
                pool.terminate()  # Terminate all tasks if timeout occurs
                tasks_are_not_completed = True  # Mark that not all tasks have completed
                break

            # Remove tasks that have already completed (they are marked as 'ready')
            task_results = [task for task in task_results if not task.ready()]
            time.sleep(0.1)  # Sleep to avoid tight looping

        pool.join()  # Ensure all worker processes have completed
    # Collect all the results from the result queue
    task_results_data = []
    while not result_queue.empty():
        task_results_data.append(result_queue.get())
    # Determine the overall status based on individual task results
    if tasks_are_not_completed:
        overall_status = "TIMEOUT"  # If timeout occurred before completion, set status as "TIMEOUT"
    else:
        # Check if all tasks failed, all succeeded, or if there was a mix (partial success)
        all_failed = all(result["status"] == "FAILED" for result in task_results_data)
        overall_status = "FAILED" if all_failed else "SUCCESS" if all(result["status"] == "SUCCESS" for result in task_results_data) else "PARTIAL"
    # Log the final status of task execution
    with log_lock:
        standard_logger.info(f"Task execution finished with overall status: {overall_status}")
    # Return the overall status and the results of each task
    return overall_status, task_results_data
