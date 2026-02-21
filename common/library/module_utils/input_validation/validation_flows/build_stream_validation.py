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
# pylint: disable=import-error,no-name-in-module,too-many-positional-arguments,too-many-arguments,unused-argument
"""
Validates build stream configuration files for Omnia.
"""
import ipaddress
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg as msg

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path
load_yaml_as_json = validation_utils.load_yaml_as_json


def validate_build_stream_config(input_file_path, data,
                                  logger, module, omnia_base_dir,
                                  module_utils_base, project_name):
    """
    Validates build stream configuration by checking enable_build_stream field,
    build_stream_host_ip, and aarch64_inventory_host_ip.
    
    Args:
        input_file_path (str): The path to the input file.
        data (dict): The data to be validated.
        logger (Logger): The logger object.
        module (AnsibleModule): The Ansible module object.
        omnia_base_dir (str): The base directory of Omnia.
        module_utils_base (str): The base directory of module_utils.
        project_name (str): The name of the project.
    
    Returns:
        list: A list of errors encountered during validation.
    """
    errors = []
    build_stream_yml = create_file_path(input_file_path, file_names["build_stream_config"])
    
    # Validate enable_build_stream
    enable_build_stream = data.get("enable_build_stream")
    
    if enable_build_stream is None:
        errors.append(create_error_msg(build_stream_yml, "enable_build_stream", 
                                       msg.ENABLE_BUILD_STREAM_REQUIRED_MSG))
    elif not isinstance(enable_build_stream, bool):
        errors.append(create_error_msg(build_stream_yml, "enable_build_stream", 
                                       msg.ENABLE_BUILD_STREAM_BOOLEAN_MSG))
    
    # Load network_spec.yml to get admin IP and netmask
    network_spec_path = create_file_path(input_file_path, file_names["network_spec"])
    network_spec_data = load_yaml_as_json(network_spec_path, omnia_base_dir, project_name, logger, module)
    
    if not network_spec_data:
        # If network_spec is not available, skip IP validations
        return errors
    
    # Extract admin network details
    admin_ip = None
    netmask_bits = None
    
    for network in network_spec_data.get("Networks", []):
        if "admin_network" in network:
            admin_network = network["admin_network"]
            admin_ip = admin_network.get("primary_oim_admin_ip")
            netmask_bits = admin_network.get("netmask_bits")
            break
    
    if not admin_ip or not netmask_bits:
        # Cannot validate without admin network info
        return errors
    
    # Validate build_stream_host_ip (optional field)
    build_stream_host_ip = data.get("build_stream_host_ip")
    
    if build_stream_host_ip and build_stream_host_ip not in ["", None]:
        # Check if it's a valid IP format (already validated by schema, but double-check)
        try:
            ipaddress.IPv4Address(build_stream_host_ip)
        except ValueError:
            errors.append(create_error_msg(build_stream_yml, "build_stream_host_ip",
                                          "Invalid IPv4 address format"))
            return errors
        
        # For now, we accept admin IP or any valid public IP
        # Note: "public IP" validation would require additional context (e.g., list of OIM public IPs)
        # Currently validating that it matches admin IP as primary check
        if build_stream_host_ip != admin_ip:
            # Log warning but don't fail - could be a valid public IP
            logger.warning(
                "build_stream_host_ip (%s) does not match admin IP (%s). "
                "Ensure this is a valid public IP of OIM if different.",
                build_stream_host_ip, admin_ip
            )
    else:
        # If not provided, admin IP will be used as default (no validation needed)
        logger.info(
            "build_stream_host_ip not provided, admin IP (%s) will be used as default",
            admin_ip
        )
    
    # Validate aarch64_inventory_host_ip
    aarch64_inventory_host_ip = data.get("aarch64_inventory_host_ip")
    
    if aarch64_inventory_host_ip and aarch64_inventory_host_ip not in ["", None]:
        # Check if it's a valid IP format
        try:
            aarch64_ip = ipaddress.IPv4Address(aarch64_inventory_host_ip)
        except ValueError:
            errors.append(create_error_msg(build_stream_yml, "aarch64_inventory_host_ip",
                                          "Invalid IPv4 address format"))
            return errors
        
        # Check if it's in the same subnet as admin IP
        try:
            admin_network = ipaddress.IPv4Network(f"{admin_ip}/{netmask_bits}", strict=False)
            
            if aarch64_ip not in admin_network:
                errors.append(create_error_msg(
                    build_stream_yml,
                    "aarch64_inventory_host_ip",
                    msg.AARCH64_INVENTORY_HOST_IP_INVALID_SUBNET_MSG
                ))
        except ValueError as e:
            logger.error("Failed to validate subnet for aarch64_inventory_host_ip: %s", str(e))
    
    return errors
