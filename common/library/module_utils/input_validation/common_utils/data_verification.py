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
"""
This module contains functions for verifying the existence of files and directories.
"""
#!/usr/bin/python

import os


# Function to verify if a file exists at the given path
def file_exists(file_path, module, logger):
    """
    Verify if a file exists at the given path.

    Args:
        file_path (str): The path of the file.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    if os.path.exists(file_path) and os.path.isfile(file_path):
        message = f"The file {file_path} exists"
        logger.info(message)
        return True
    message = f"The file {file_path} does not exist"
    logger.error(message)
    module.fail_json(msg=message)
    return False


# Function to verify if a directory exists at the given path
def directory_exists(directory_path, module, logger):
    """
    Verify if a directory exists at the given path.

    Args:
        directory_path (str): The path of the directory to check.

    Returns:
        bool: True if the directory exists, False otherwise.
    """
    if os.path.exists(directory_path) and os.path.isdir(directory_path):
        message = f"The directory {directory_path} exists."
        logger.info(message)
        return True
    message = f"The directory {directory_path} does not exist."
    logger.error(message)
    module.fail_json(msg=message)
    return False
