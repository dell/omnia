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

import json
import os
import re
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg
from ansible.module_utils.input_validation.validation_flows import common_validation

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path

def validate_provision_config(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    errors = []
    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    software_config_json = json.load(open(software_config_file_path, "r"))

     # Call validate_software_config from common_validation
    software_errors = common_validation.validate_software_config(
        input_file_path,
        software_config_json,
        logger,
        module,
        omnia_base_dir,
        module_utils_base,
        project_name
    )
    errors.extend(software_errors)

    # Validate disk partition duplicates
    if "disk_partition" in data:
        mount_points = [partition.get('mount_point') for partition in data["disk_partition"]]
        unique_mount_points = set(mount_points)
        if len(mount_points) != len(unique_mount_points):
            errors.append(create_error_msg(
                "disk_partition",
                input_file_path,
                en_us_validation_msg.disk_partition_fail_msg
            ))

    # Validate language setting
    language = data.get("language", "")
    if not language:
        errors.append(create_error_msg(
            "language",
            input_file_path,
            en_us_validation_msg.language_empty_msg
        ))
    elif "en-US" not in language:
        errors.append(create_error_msg(
            "language",
            input_file_path,
            en_us_validation_msg.language_fail_msg
        ))

    # Validate domain name
    domain_name = data.get("domain_name", "")
    domain_pattern = r'^[a-zA-Z0-9.-]+$'
    if not domain_name or not re.match(domain_pattern, domain_name):
        errors.append(create_error_msg(
            "domain_name",
            domain_name,
            en_us_validation_msg.domain_name_fail_msg
        ))

    timezone_file_path = os.path.join(module_utils_base,'input_validation','common_utils','timezone.txt')
    pxe_mapping_file_path = data.get("pxe_mapping_file_path", '')
    if pxe_mapping_file_path and not (validation_utils.verify_path(pxe_mapping_file_path)):
        errors.append(create_error_msg("pxe_mapping_file_path", pxe_mapping_file_path, en_us_validation_msg.pxe_mapping_file_path_fail_msg))

    timezone = data["timezone"]
    if not (validation_utils.validate_timezone(timezone, timezone_file_path)):
        errors.append(create_error_msg("timezone", timezone, en_us_validation_msg.timezone_fail_msg))

    default_lease_time = data["default_lease_time"]
    if not (validation_utils.validate_default_lease_time(default_lease_time)):
        errors.append(create_error_msg("default_lease_time", default_lease_time, en_us_validation_msg.default_lease_time_fail_msg))

     # Validate NTP support
    ntp_support = data["ntp_support"]
    if ntp_support is None or ntp_support == "":
        errors.append(create_error_msg("ntp_support", ntp_support, en_us_validation_msg.ntp_support_empty_msg))

    return errors

def validate_network_spec(input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name):
    """
    Validates the network specification configuration.

    Args:
        input_file_path (str): Path to the input configuration file
        data (dict): The network specification data to validate
        logger (Logger): Logger instance for logging messages
        module (AnsibleModule): Ansible module instance
        omnia_base_dir (str): Base directory path for Omnia
        module_utils_base (str): Base path for module utilities
        project_name (str): Name of the project

    Returns:
        list: List of validation errors, empty if no errors found
    """
    errors = []

    if not data.get("Networks"):
        errors.append(create_error_msg(
            "Networks",
            None,
            en_us_validation_msg.admin_network_missing_msg
        ))
        return errors

    for network in data["Networks"]:
        errors.extend(_validate_admin_network(network))
        errors.extend(_validate_bmc_network(network))

    return errors

def _validate_admin_network(network):
    """
    Validates the admin network configuration.

    Args:
        network (dict): Admin network configuration dictionary containing network settings

    Returns:
        list: List of validation errors for admin network, empty if no errors found

    Validates:
        - Netmask bits
        - Network gateway
        - Static and dynamic IP ranges
    """
    errors = []
    if "admin_network" not in network:
        return errors

    admin_net = network["admin_network"]

    # Validate netmask_bits
    if "netmask_bits" in admin_net:
        netmask = admin_net["netmask_bits"]
        if not validation_utils.validate_netmask_bits(netmask):
            errors.append(create_error_msg(
                "admin_network.netmask_bits",
                netmask,
                en_us_validation_msg.netmask_bits_fail_msg
            ))

    # Validate network gateway
    if "network_gateway" in admin_net and admin_net["network_gateway"]:
        gateway = admin_net["network_gateway"]
        if not validation_utils.validate_ipv4_range(gateway):
            errors.append(create_error_msg(
                "admin_network.network_gateway",
                gateway,
                en_us_validation_msg.network_gateway_fail_msg
            ))

    # Validate IP ranges
    if "static_range" in admin_net and "dynamic_range" in admin_net:
        errors.extend(_validate_ip_ranges(
            admin_net["static_range"],
            admin_net["dynamic_range"],
            "admin_network",
            netmask
        ))

    return errors

def _validate_bmc_network(network):
    """
    Validates the BMC (Baseboard Management Controller) network configuration.

    Args:
        network (dict): BMC network configuration dictionary containing network settings

    Returns:
        list: List of validation errors for BMC network, empty if no errors found

    Validates:
        - Netmask bits
        - Network gateway
        - Dynamic range and dynamic conversion static range
    """
    errors = []
    if "bmc_network" not in network:
        return errors

    bmc_net = network.get("bmc_network", {})

    # Skip validation if BMC network is empty
    if not any(bmc_net.values()):
        return errors

    # Validate netmask_bits
    if bmc_net.get("netmask_bits"):
        netmask = bmc_net["netmask_bits"]
        if not validation_utils.validate_netmask_bits(netmask):
            errors.append(create_error_msg(
                "bmc_network.netmask_bits",
                netmask,
                en_us_validation_msg.netmask_bits_fail_msg
            ))

    # Validate network gateway
    if bmc_net.get("network_gateway"):
        gateway = bmc_net["network_gateway"]
        if not validation_utils.validate_ipv4_range(gateway):
            errors.append(create_error_msg(
                "bmc_network.network_gateway",
                gateway,
                en_us_validation_msg.network_gateway_fail_msg
            ))

    # Validate IP ranges
    if bmc_net.get("dynamic_range") and bmc_net.get("dynamic_conversion_static_range"):
        errors.extend(_validate_ip_ranges(
            bmc_net["dynamic_conversion_static_range"],
            bmc_net["dynamic_range"],
            "bmc_network",
            netmask
        ))

    return errors

def _validate_ip_ranges(static_range, dynamic_range, network_type, netmask_bits):
    """
    Validates and checks for overlap between static and dynamic IP ranges.

    Args:
        static_range (str): IP range for static addresses (format: "start_ip-end_ip")
        dynamic_range (str): IP range for dynamic addresses (format: "start_ip-end_ip")
        network_type (str): Type of network being validated ("admin_network" or "bmc_network")
        netmask_bits (str): The netmask bits value to validate IP ranges against

    Returns:
        list: List of validation errors for IP ranges, empty if no errors found

    Validates:
        - IP range format
        - Overlap between static and dynamic ranges
        - IP ranges are within valid netmask boundaries
    """
    errors = []

    # Validate range formats
    if not validation_utils.validate_ipv4_range(static_range):
        errors.append(create_error_msg(
            f"{network_type}.static_range",
            static_range,
            en_us_validation_msg.range_ip_check_fail_msg
        ))

    if not validation_utils.validate_ipv4_range(dynamic_range):
        errors.append(create_error_msg(
            f"{network_type}.dynamic_range",
            dynamic_range,
            en_us_validation_msg.range_ip_check_fail_msg
        ))

    # Check for overlap if both ranges are valid
    if validation_utils.validate_ipv4_range(static_range) and validation_utils.validate_ipv4_range(dynamic_range):
        does_overlap, _ = validation_utils.check_overlap([static_range, dynamic_range])
        if does_overlap:
            range_info = {
                "static_range": static_range,
                "dynamic_range": dynamic_range
            }
            errors.append(create_error_msg(
                f"{network_type}.ranges",
                range_info,
                en_us_validation_msg.range_ip_check_overlap_msg
            ))

    # Validate that IP ranges are within the netmask boundaries
    if netmask_bits:
        # Check static range
        if (validation_utils.validate_ipv4_range(static_range) and
            not validation_utils.is_range_within_netmask(static_range, netmask_bits)):
            errors.append(create_error_msg(
                f"{network_type}.static_range",
                static_range,
                en_us_validation_msg.range_netmask_boundary_fail_msg
            ))

        # Check dynamic range
        if (validation_utils.validate_ipv4_range(dynamic_range) and
            not validation_utils.is_range_within_netmask(dynamic_range, netmask_bits)):
            errors.append(create_error_msg(
                f"{network_type}.dynamic_range",
                dynamic_range,
                en_us_validation_msg.range_netmask_boundary_fail_msg
            ))

    return errors
