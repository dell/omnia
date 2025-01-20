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

#data_collector_psutil.py
#!/usr/bin/env python3
'''
	Module to get metrics using psutil library.
'''
import psutil
import common_logging

def get_cpu_time_info():
    '''
    Get CPU time information using psutil.
    '''
    try:
        cpu_times_info = psutil.cpu_times()
        return cpu_times_info
    except psutil.Error as exc:
        # Log the error with exception details using common_logging.log_error
        common_logging.log_error('data_collector_psutil:get_cpu_time_info', f"Error occurred while getting CPU time information: {exc}")
        return None

def get_packet_info():
    '''
    Get packet information using psutil.
    '''
    try:
        packet_info = psutil.net_io_counters(pernic=True)
        return packet_info
    except psutil.Error as exc:
        # Log the error with exception details using common_logging.log_error
        common_logging.log_error('data_collector_psutil:get_packet_info', f"Error occurred while getting packet information: {exc}")
        return None

def get_memory_info():
    '''
    Get memory information using psutil.
    '''
    try:
        memory_info = psutil.virtual_memory()
        return memory_info
    except psutil.Error as exc:
        # Log the error with exception details using common_logging.log_error
        common_logging.log_error('data_collector_psutil:get_memory_info', f"Error occurred while getting memory information: {exc}")
        return None
