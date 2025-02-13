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
import threading
import queue
import time

def setup_standard_logger(log_dir, log_filename="standard.log"):
    """
    Sets up a standard logger to log to a specified file.
 
    Parameters:
        log_dir (str): The directory where the log file will be saved.
        log_filename (str, optional): The name of the log file. Defaults to "standard.log".
 
    Returns:
        logging.Logger: The configured logger instance.
    """
    # Ensure the log directory exists
    os.makedirs(log_dir, exist_ok=True)
 
    log_filepath = os.path.join(log_dir, log_filename)
   
    # Create a logger
    logger = logging.getLogger("task_logger")
    logger.setLevel(logging.DEBUG)
   
    # Create file handler and set level to debug
    file_handler = logging.FileHandler(log_filepath)
    file_handler.setLevel(logging.DEBUG)
   
    # Create a console handler for error-level logging to stdout
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
   
    # Create formatter and add it to handlers
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
   
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
   
    return logger
