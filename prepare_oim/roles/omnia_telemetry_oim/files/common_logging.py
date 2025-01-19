# Copyright 2023 Dell Inc. or its subsidiaries. All Rights Reserved.
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


'''
Module for common logging 
'''
import syslog

def setup_syslog(ident):
    '''
    Set up syslog with appropriate facility and logging level.

    Args:
        ident (str): The identifier to be used for syslog.
    '''
    syslog.openlog(ident=ident, facility=syslog.LOG_LOCAL0)

def log_error(module_name_function_name, error_message):
    '''
    Log an error message to syslog.

    Args:
        module_name_function_name (str): The identifier associated with the log message.
        error_message (str): The error message to be logged.
    '''
    syslog.syslog(syslog.LOG_ERR, f"{module_name_function_name}: {error_message}")

def log_message(module_name_function_name, info_message):
    '''
    Log info message to syslog.

    Args:
        module_name_function_name (str): The identifier associated with the log message.
        info_message (str): The message to be logged.
    '''
    syslog.syslog(syslog.LOG_INFO, f"{module_name_function_name}: {info_message}")

def close_syslog():
    '''
    Close the syslog connection.
    '''
    syslog.closelog()
