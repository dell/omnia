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
This module contains utility functions for input validation in the telemetry domain.
"""
import os
import yaml
from ansible.module_utils.input_validation.messages import en_us_validation_msg

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

def is_string_empty(value):
    """
    Checks if a string is empty.

    Args:
        value (str): The string to check.

    Returns:
        bool: True if the string is empty, False otherwise.
    """
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return len(value.strip()) < 1
