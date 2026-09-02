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
import json
import traceback
import yaml
import requests
from cryptography.fernet import Fernet
from jinja2 import Template
from ansible.module_utils.repo_manager.common_functions import (
    load_yaml_file,
    load_vault_yaml
)
from ansible.module_utils.repo_manager.registry_utils import resolve_registry_contexts
# Global lock for logging synchronization
log_lock = multiprocessing.Lock()
docker_password_cipher = Fernet(Fernet.generate_key())
PROGRESS_LOG_INTERVAL_SECONDS = 60


def load_docker_credentials(vault_yml_path, vault_password_file):
    """
    Loads docker_username and docker_password from a credentials YAML file,
    decrypting it with Ansible Vault only when the file is actually encrypted,
    and validates the credentials using the Docker Hub API.

    Validation Logic:
        - If the file is vault-encrypted, decrypts it using ansible-vault view.
        - If the file is plain YAML (e.g. during upgrade staging), reads it directly.
        - Validates credentials via Docker Hub REST API
        - Returns credentials if authentication succeeds (HTTP 200)
        - Raises RuntimeError for all authentication failures

    Args:
        vault_yml_path (str): Path to the Ansible Vault YAML file (may or may not be encrypted).
        vault_password_file (str): Path to the vault password file (used only when encrypted).

    Returns:
        tuple: (docker_username, docker_password) or (None, None) if not provided.

    Raises:
        RuntimeError: If vault decryption fails, YAML parsing fails, Docker Hub API
                     authentication fails, network errors occur, or requests module
                     is not installed.
    """
    try:
        data = load_vault_yaml(vault_yml_path, vault_password_file)
        docker_username = data.get("docker_username")
        docker_secret_token = None
        if data.get("docker_password"):
            docker_secret_token = docker_password_cipher.encrypt(
                data.get("docker_password").encode("utf-8")
            ).decode("utf-8")

        # If either credential is missing, skip validation
        if not docker_username or not docker_secret_token:
            return None, None

        # Validate credentials using Docker Hub API
        try:
            validation_secret = docker_password_cipher.decrypt(
                docker_secret_token.encode("utf-8")
            ).decode("utf-8")
            payload = json.dumps({"username": docker_username, "password": validation_secret})
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
                return docker_username, docker_secret_token

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
        with open(log_file, "w", encoding="utf-8") as file:
            file.write("Command Execution Results Table:\n")  # Add a header to the table
            file.write(table_output)  # Write the actual table content
    except Exception as e:
        # If there is an error, raise a RuntimeError with the error message
        raise RuntimeError(f"Failed to write table output to log file: {str(e)}")


def setup_logger(log_dir, log_file_path):
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
        formatter = logging.Formatter('%(asctime)s - %(levelname)-7s - [%(filename)s] - %(message)s')
        # Apply the formatter to the file handler
        file_handler.setFormatter(formatter)
        # Add the file handler to the logger
        logger.addHandler(file_handler)
    return logger


def execute_task(task, determine_function, user_data, version_variables, arc,
                repo_store_path, csv_file_path, logger, registry_contexts,
                docker_username, docker_secret_token, timeout=None):
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
        registry_contexts (dict): Configured registries resolved with credentials

    Returns:
        dict: A dictionary containing the task information, its execution status,
              any output, and any errors.
    """
    try:
        start_time = time.time()  # Track the start time of the task execution
        with log_lock:
            logger.info(f"### {execute_task.__name__} start ###")  # Log task start

        # Build package display name with tag for images
        package_display = task.get("package", "")
        if task.get("type") == "image" and "tag" in task:
            package_display = f"{package_display}:{task['tag']}"
        elif task.get("type") == "image" and "digest" in task:
            package_display = f"{package_display}:{task['digest']}"

        # Determine the function and its arguments using the provided `determine_function`
        function, args = determine_function(task, repo_store_path, csv_file_path, user_data,
                         version_variables, arc, registry_contexts, docker_username, docker_secret_token)

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
                    "package": package_display,
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
            logger.info(f"Task {function.__name__} completed.")
            logger.info(f"### {execute_task.__name__} end ###")

        return {
            "task": task,
            "package": package_display,
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
            "package": package_display,
            "status": "FAILED",
            "output": "",
            "error": str(e)  # Include the error message
        }


def _requires_docker_hub_credentials(task, registry_contexts):
    """Return whether this task uses the legacy Docker Hub credential path."""
    if task.get("type") != "image":
        return False

    source_registry = task.get("source_registry", "")
    if source_registry and source_registry in (registry_contexts or {}):
        return False

    package = task.get("package", "")
    return source_registry in ("docker.io", "registry-1.docker.io") or package.startswith(
        ("docker.io/", "registry-1.docker.io/")
    )


def worker_process(task, determine_function, user_data, version_variables, arc, repo_store_path,
                  csv_file_path, log_dir, registry_contexts,
                  omnia_credentials_yaml_path, omnia_credentials_vault_path, timeout,
                  state_lock, resource_lock, dnf_semaphore):
    """Execute one task and return exactly one result to the parent process."""
    thread_log_path = os.path.join(log_dir, f"package_status_{os.getpid()}.log")
    logger = setup_logger(log_dir, thread_log_path)
    try:
        # Artifact modules historically supplied separate module-local locks to
        # the common status writer. Replace those locks with one manager-backed
        # lock for the status CSV and mirror-index read/modify/write transaction.
        from ansible.module_utils.repo_manager.parse_and_download import (  # pylint: disable=import-outside-toplevel
            configure_status_file_lock,
        )
        configure_status_file_lock(state_lock)

        with log_lock:
            logger.info("Worker process %d started execution.", os.getpid())

        if _requires_docker_hub_credentials(task, registry_contexts):
            docker_username, docker_secret_token = load_docker_credentials(
                omnia_credentials_yaml_path, omnia_credentials_vault_path)
        else:
            docker_username, docker_secret_token = None, None

        # Different resources remain parallel. Tasks that share a Pulp resource
        # (notably multiple tags of one image) are serialized end to end. RPM
        # tasks additionally share a DNF semaphore so the per-architecture DNF
        # metadata cache remains safe when the general worker pool is increased.
        dnf_slot_acquired = False
        if task.get("type") in ("rpm", "rpm_repo"):
            logger.info("Waiting for an available DNF command slot")
            dnf_semaphore.acquire()
            dnf_slot_acquired = True
            logger.info("Acquired DNF command slot")
        try:
            with resource_lock:
                result = execute_task(
                    task, determine_function, user_data, version_variables, arc,
                    repo_store_path, csv_file_path, logger, registry_contexts,
                    docker_username, docker_secret_token, timeout
                )
        finally:
            if dnf_slot_acquired:
                dnf_semaphore.release()
                logger.info("Released DNF command slot")
        result["logname"] = f"package_status_{os.getpid()}.log"

        with log_lock:
            logger.info("Worker process %d completed task execution.", os.getpid())
        return result
    except Exception:  # pylint: disable=broad-exception-caught
        with log_lock:
            logger.error("Worker process %s encountered an internal error.", os.getpid())
            logger.error("Traceback:\n%s", traceback.format_exc())
        return {
            "task": task,
            "package": task.get("package", task.get("Name", "unknown")),
            "status": "FAILED",
            "output": "",
            "error": "Task execution failed due to an internal error.",
            "logname": f"package_status_{os.getpid()}.log",
        }


def _task_identity(task):
    """Return a deterministic identity that retains distinct tags and sources."""
    return (
        task.get("type", ""),
        task.get("package", ""),
        task.get("tag", ""),
        task.get("digest", ""),
        task.get("source_registry", ""),
    )


def _task_resource_key(task):
    """Return the shared Pulp resource targeted by a task."""
    task_type = task.get("type", "")
    package = task.get("package", task.get("Name", ""))
    if task_type == "image":
        # Tags and digests of one image share its repository and remote.
        return f"image:{package}"
    return f"{task_type}:{package}"


def _failed_worker_result(task, error_message, status="FAILED"):
    """Build a stable result when a worker cannot return normally."""
    return {
        "task": task,
        "package": task.get("package", task.get("Name", "unknown")),
        "status": status,
        "output": "",
        "error": error_message,
        "logname": "N/A",
    }


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
    timeout,
    dnf_max_concurrent_commands=1
):
    """
    Executes a list of tasks in parallel using multiple worker processes.
    Args:
        tasks (list): A list of tasks (dictionaries) that need to be processed in parallel.
        determine_function (function): A function that determines which function to
        execute and its arguments for each task.
        nthreads (int): The number of worker processes to run in parallel.
        dnf_max_concurrent_commands (int): Maximum RPM tasks allowed to use
            DNF concurrently, independent of the general worker count.
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
    with log_lock:
        standard_logger.info("Starting parallel task execution.")

    if not 1 <= int(nthreads) <= 5:
        raise ValueError("nthreads must be between 1 and 5")
    if not 1 <= int(dnf_max_concurrent_commands) <= 5:
        raise ValueError("dnf_max_concurrent_commands must be between 1 and 5")

    config = load_yaml_file(local_repo_config_path)
    credential_data = load_vault_yaml(
        omnia_credentials_yaml_path, omnia_credentials_vault_path
    )
    registry_contexts = resolve_registry_contexts(
        config.get("registries") or {}, credential_data
    )

    # Render before deduplication so identities and locks match actual Pulp names.
    seen_packages = set()
    deduplicated_tasks = []
    for task in tasks:
        rendered_task = dict(task)
        package_template = Template(rendered_task.get("package") or "")
        rendered_task["package"] = package_template.render(**version_variables)
        package_key = _task_identity(rendered_task)

        if package_key not in seen_packages:
            seen_packages.add(package_key)
            deduplicated_tasks.append(rendered_task)
        else:
            standard_logger.info(f"Skipping duplicate task: {package_key}")

    tasks = deduplicated_tasks
    if not tasks:
        return "SUCCESS", []

    effective_workers = min(int(nthreads), len(tasks))
    standard_logger.info(
        "Configured package workers: %d; effective workers: %d",
        int(nthreads), effective_workers
    )
    effective_dnf_commands = min(
        int(dnf_max_concurrent_commands), effective_workers
    )
    standard_logger.info(
        "Configured concurrent DNF commands: %d; effective limit: %d",
        int(dnf_max_concurrent_commands), effective_dnf_commands
    )
    standard_logger.info("Detailed worker logs: %s", log_dir)

    tasks_are_not_completed = False
    task_results_data = []
    with multiprocessing.Manager() as manager:
        state_lock = manager.RLock()
        dnf_semaphore = manager.BoundedSemaphore(effective_dnf_commands)
        resource_locks = {}
        with multiprocessing.Pool(processes=effective_workers) as pool:
            async_results = []

            for task in tasks:
                resource_key = _task_resource_key(task)
                if resource_key not in resource_locks:
                    resource_locks[resource_key] = manager.RLock()
                async_result = pool.apply_async(
                    worker_process,
                    (
                        task, determine_function, user_data, version_variables, arc,
                        repo_store_path, csv_file_path, log_dir, registry_contexts,
                        omnia_credentials_yaml_path, omnia_credentials_vault_path,
                        timeout, state_lock, resource_locks[resource_key],
                        dnf_semaphore,
                    ),
                )
                async_results.append((task, async_result))

            pool.close()
            start_time = time.time()
            last_progress_log_time = start_time
            while any(not result.ready() for _, result in async_results):
                current_time = time.time()
                elapsed_time = current_time - start_time
                if timeout and elapsed_time > timeout:
                    with log_lock:
                        standard_logger.warning(
                            f"Overall timeout reached ({elapsed_time:.2f}s), "
                            "stopping remaining tasks."
                        )
                    pool.terminate()
                    tasks_are_not_completed = True
                    break
                if current_time - last_progress_log_time >= PROGRESS_LOG_INTERVAL_SECONDS:
                    finished_count = sum(
                        1 for _, result in async_results if result.ready()
                    )
                    total_count = len(async_results)
                    elapsed_seconds = int(elapsed_time)
                    with log_lock:
                        standard_logger.info(
                            "Progress: finished=%d/%d, remaining=%d, "
                            "elapsed=%dm %ds, workers=%d, logs=%s",
                            finished_count, total_count,
                            total_count - finished_count,
                            elapsed_seconds // 60, elapsed_seconds % 60,
                            effective_workers, log_dir
                        )
                    last_progress_log_time = current_time
                time.sleep(0.1)

            pool.join()

            for task, async_result in async_results:
                if tasks_are_not_completed and not async_result.ready():
                    task_results_data.append(
                        _failed_worker_result(
                            task, "Task stopped after the overall timeout.",
                            status="TIMEOUT"
                        )
                    )
                    continue
                try:
                    task_results_data.append(async_result.get())
                except Exception as error:  # pylint: disable=broad-exception-caught
                    standard_logger.error("Worker result collection failed: %s", error)
                    task_results_data.append(
                        _failed_worker_result(
                            task, "Worker process did not return a result."
                        )
                    )

    if len(task_results_data) != len(tasks):
        raise RuntimeError(
            f"Expected {len(tasks)} worker results, received {len(task_results_data)}"
        )

    # Determine the overall status based on individual task results
    if tasks_are_not_completed:
        overall_status = "TIMEOUT"  # If timeout occurred before completion, set status as "TIMEOUT"
    else:
        # Check if all tasks failed, all succeeded, or if there was a mix (partial success)
        all_failed = all(result["status"] == "FAILED" for result in task_results_data)
        all_succeeded = all(
            result["status"] == "SUCCESS" for result in task_results_data
        )
        overall_status = "FAILED" if all_failed else "SUCCESS" if all_succeeded else "PARTIAL"
    # Log the final status of task execution
    with log_lock:
        standard_logger.info(
            "Task execution finished with overall status: %s", overall_status
        )
    # Return the overall status and the results of each task
    return overall_status, task_results_data
