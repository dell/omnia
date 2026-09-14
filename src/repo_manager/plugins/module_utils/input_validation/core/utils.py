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
Common utility functions for input validation.

This module provides the error and path helpers used by Repo Manager input
validation.
"""

# =============================================================================
# ERROR MESSAGE UTILITIES
# =============================================================================


def create_error_msg(key, value, msg):
    """
    Creates an error message dictionary.

    Args:
        key (str): The key of the error.
        value (str): The value of the error.
        msg (str): The error message.

    Returns:
        dict: The error message dictionary.
    """
    return {"error_key": key, "error_value": value, "error_msg": msg}


def create_file_path(input_file_path, other_file):
    """
    Creates a file path by replacing the last part of the input file path.

    Args:
        input_file_path (str): The input file path.
        other_file (str): The name of the other file.

    Returns:
        str: The new file path.
    """
    path_parts = input_file_path.split("/")
    path_parts[-1] = other_file
    return "/".join(path_parts)







# =============================================================================
# IP ADDRESS UTILITIES
# =============================================================================



















# =============================================================================
# PASSWORD VALIDATION
# =============================================================================







# =============================================================================
# PORT VALIDATION
# =============================================================================





# =============================================================================
# DATA VALIDATION UTILITIES
# =============================================================================









# =============================================================================
# CLUSTER ITEM VALIDATION
# =============================================================================
