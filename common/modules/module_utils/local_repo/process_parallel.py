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

import os
import logging
import multiprocessing
import time
import threading
from jinja2 import Template

# Global lock for logging synchronization
log_lock = multiprocessing.Lock()

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

def execute_task(task, determine_function, user_data, version_variables, repo_store_path, csv_file_path,logger, timeout=None):

    """
    Executes a task by determining the appropriate function to call, managing execution time, 
    handling timeouts, and logging the results.

    Args:
        task (dict): The task to execute, expected to contain necessary details such as "package".
        determine_function (function): A function that takes a task, repo_store_path, and csv_file_path 
                                        and returns the function to call and its arguments.
        repo_store_path (str): The path to the repository where files are stored.
        csv_file_path (str): Path to a CSV file to be processed as part of the task.
        logger (logging.Logger): The logger instance for logging the task's execution.
        timeout (float, optional): The maximum time allowed for the task to execute. If `None`, no timeout is enforced.

    Returns:
        dict: A dictionary containing the task information, its execution status, any output, and any errors.
    """

    try:
        start_time = time.time()  # Track the start time of the task execution
        with log_lock:
            logger.info(f"### {execute_task.__name__} start ###")  # Log task start

        # Determine the function and its arguments using the provided `determine_function`
        function, args = determine_function(task, repo_store_path, csv_file_path, user_data, version_variables)

        while True:
            elapsed_time = time.time() - start_time  # Calculate elapsed time
            logger.info(f"--->{elapsed_time:.2f}s.")  # Log the elapsed time

            # Check if the timeout has been reached
            if timeout and elapsed_time > timeout:
                with log_lock:
                    logger.info(f"Timeout reached ({elapsed_time:.2f}s), stopping task execution for {task}.")
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

def worker_process(task, determine_function, user_data,version_variables, repo_store_path, csv_file_path, log_dir, result_queue, timeout):

    """
    Executes a task in a separate worker process, logs the process execution, and puts the result in a result queue.

    Args:
        task (dict): The task to be processed, containing details like the package to be processed.
        determine_function (function): A function that determines the function to call and its arguments for the task.
        repo_store_path (str): Path to the repository where task-related files are stored.
        csv_file_path (str): Path to a CSV file that may be needed for processing the task.
        log_dir (str): Directory where log files for the worker process should be saved.
        result_queue (multiprocessing.Queue): Queue for putting the result of the task execution (used for inter-process communication).
        timeout (float): The maximum allowed time for the task execution.

    Returns:
        None: The result is placed into the `result_queue`, so no return value is needed.
    """
    # Define the log file path for the current worker process using the process name (ensures unique log files)
    #thread_log_path = os.path.join(log_dir, f"task_{multiprocessing.current_process().name}_log.log")

    #Define the log file path using process ID for uniqueness
    thread_log_path = os.path.join(log_dir, f"package_status_{os.getpid()}.log")

    # Setup logger specific to this worker process
    logger = setup_logger(log_dir,thread_log_path)

    try:
        # Log the start of the worker process execution
        with log_lock:
           # logger.info(f"Worker process {multiprocessing.current_process().name} started  execution.")
           logger.info(f"Worker process {os.getpid()} started  execution.")

        # Execute the task by calling the `execute_task` function and passing necessary arguments
        result = execute_task(task, determine_function, user_data, version_variables, repo_store_path, csv_file_path, logger, timeout)

        result["logname"] = f"package_status_{os.getpid()}.log"
        # Put the result of the task execution into the result_queue for further processing
        result_queue.put(result)

        # Log the successful completion of the task execution
        with log_lock:
           # logger.info(f"Worker process {multiprocessing.current_process().name} completed task execution.")
            logger.info(f"Worker process {os.getpid()} completed task execution.")
    except Exception as e:
        # Log any errors encountered during task execution
        with log_lock:
            #logger.error(f"Worker process {multiprocessing.current_process().name} encountered an error: {str(e)}")
            logger.error(f"Worker process {os.getpid()} encountered an error: {str(e)}")

        # If an error occurs, put a failure result in the queue indicating task failure
        result_queue.put({"task": task, "status": "FAILED", "output": "", "error": str(e)})

    
def execute_parallel(tasks, determine_function, nthreads, repo_store_path, csv_file_path,log_dir, user_data, version_variables, standard_logger, timeout):
    
    """
    Executes a list of tasks in parallel using multiple worker processes.

    Args:
        tasks (list): A list of tasks (dictionaries) that need to be processed in parallel.
        determine_function (function): A function that determines which function to execute and its arguments for each task.
        nthreads (int): The number of worker processes to run in parallel.
        repo_store_path (str): Path to the repository where task-related files are stored.
        csv_file_path (str): Path to a CSV file that may be needed for processing some tasks.
        log_dir (str): Directory where log files for the worker processes will be saved.
        standard_logger (logging.Logger): A shared logger for overall task execution.
        timeout (float, optional): The maximum time allowed for all tasks to execute. If `None`, no timeout is enforced.

    Returns:
        tuple: A tuple containing:
            - overall_status (str): The overall status of task execution ("SUCCESS", "FAILED", "PARTIAL", "TIMEOUT").
            - task_results_data (list): A list of dictionaries, each containing the result of an individual task.
    """
    # Create a shared queue for collecting task results from worker processes
    result_queue = multiprocessing.Manager().Queue()

    with log_lock:
        standard_logger.info("Starting parallel task execution.")  # Log the start of parallel execution

    # Create a pool of worker processes to handle the tasks
    with multiprocessing.Pool(processes=nthreads) as pool:
        task_results = []  # List to hold references to the async results of the tasks

        # Submit each task to the pool for parallel execution
        for task in tasks:
            package_template = Template(task.get('package', None))
            package_name = package_template.render(**version_variables)
            task['package'] = package_name
            task_results.append(pool.apply_async(worker_process, (task, determine_function, user_data, version_variables, repo_store_path, csv_file_path, log_dir, result_queue, timeout)))

        pool.close()  # Close the pool to new tasks once all have been submitted

        start_time = time.time()  # Start time for overall task execution
        tasks_are_not_completed = False  # Flag to track if timeout occurred before all tasks completed

        # Check the status of the tasks periodically and enforce the timeout if necessary
        while task_results:
            elapsed_time = time.time() - start_time  # Calculate elapsed time
            if timeout and elapsed_time > timeout:  # Check if overall timeout has been reached
                with log_lock:
                    standard_logger.warning(f"Overall timeout reached ({elapsed_time:.2f}s), stopping remaining tasks.")
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
