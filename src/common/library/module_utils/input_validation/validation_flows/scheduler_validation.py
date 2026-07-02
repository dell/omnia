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

# pylint: disable=import-error,no-name-in-module,too-many-positional-arguments,too-many-arguments
"""
L2 level validations for K8s scheduler
"""

from ansible.module_utils.input_validation.common_utils import validation_utils

def validate_k8s_parameters(
        admin_static_range, bmc_static_range,
        admin_dynamic_range, bmc_dynamic_range,
        k8s_service_addresses,
        k8s_pod_network_cidr):
    """
    Validates Kubernetes IP configuration to ensure there is no overlap between defined IP ranges.

    This function checks for overlapping IP ranges across various network segments, including:
    - Admin static and dynamic IP ranges
    - BMC (Baseboard Management Controller) static and dynamic IP ranges
    - Pod external IP range
    - Kubernetes service addresses
    - Kubernetes pod network CIDR

    Parameters:
        admin_static_range (str): IP range for static admin network.
        bmc_static_range (str): IP range for static BMC network.
        admin_dynamic_range (str): IP range for dynamic admin network.
        bmc_dynamic_range (str): IP range for dynamic BMC network.
        pod_external_ip_range (str): External IP range used by pods.
        k8s_service_addresses (str): IP range for Kubernetes services.
        k8s_pod_network_cidr (str): CIDR for Kubernetes pod network.

    Returns:
        list: A list of error messages. If IP ranges overlap, the list contains an error message;
    """
    # Check IP range overlap between omnia IPs, admin network, and bmc network
    results=[]
    ip_ranges = [admin_static_range, bmc_static_range,
                admin_dynamic_range, bmc_dynamic_range,
                k8s_service_addresses,
                k8s_pod_network_cidr]
    does_overlap, _ = validation_utils.check_overlap(ip_ranges)
    if does_overlap:
        results.append("The IP range define is not correct.")
    return results
