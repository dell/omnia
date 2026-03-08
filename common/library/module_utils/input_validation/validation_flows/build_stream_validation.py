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
import os
import socket
import ssl
import subprocess
from http import client
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg as msg

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path
load_yaml_as_json = validation_utils.load_yaml_as_json


def get_ethernet_interface_ips(logger):
    """
    Get all IPv4 addresses assigned to physical ethernet interfaces on the OIM.

    Uses /sys/class/net/ to identify physical ethernet interfaces
    (type=1, has 'device' symlink, not a bridge) and the `ip` command
    to retrieve all IPv4 addresses (including secondary addresses).

    Args:
        logger: Logger instance

    Returns:
        list: List of IPv4 address strings from ethernet interfaces
    """
    ethernet_ips = []
    net_dir = '/sys/class/net'

    try:
        if not os.path.isdir(net_dir):
            logger.warning("/sys/class/net directory not found")
            return ethernet_ips

        for iface in sorted(os.listdir(net_dir)):
            iface_path = os.path.join(net_dir, iface)

            # Check interface type: 1 = ARPHRD_ETHER (ethernet)
            type_file = os.path.join(iface_path, 'type')
            try:
                with open(type_file, 'r', encoding='utf-8') as f:
                    iface_type = int(f.read().strip())
            except (IOError, ValueError):
                continue
            if iface_type != 1:
                continue

            # Skip bridge interfaces (have a 'bridge' subdirectory)
            if os.path.isdir(os.path.join(iface_path, 'bridge')):
                continue

            # Skip virtual interfaces: physical NICs have a 'device' symlink
            if not os.path.exists(os.path.join(iface_path, 'device')):
                continue

            # Get all IPv4 addresses (primary + secondary) via ip command
            ip_result = subprocess.run(
                ['ip', '-4', '-o', 'addr', 'show', 'dev', iface],
                capture_output=True, text=True, timeout=10, check=False
            )
            if ip_result.returncode != 0:
                logger.debug("No IPv4 address on interface %s", iface)
                continue

            for line in ip_result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'inet' and i + 1 < len(parts):
                        ip_addr = parts[i + 1].split('/')[0]
                        if ip_addr not in ethernet_ips:
                            ethernet_ips.append(ip_addr)

        logger.debug("Valid IPs found: %s", ethernet_ips)
    except OSError as e:
        logger.warning("Failed to get ethernet interface IPs: %s", str(e))
    return ethernet_ips

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

    # Validate build_stream_host_ip (mandatory field)
    build_stream_host_ip = data.get("build_stream_host_ip")

    if not build_stream_host_ip or build_stream_host_ip in ["", None]:
        errors.append(create_error_msg(build_stream_yml, "build_stream_host_ip",
                                       msg.BUILD_STREAM_HOST_IP_REQUIRED_MSG))
        return errors

    # Check if it's a valid IP format
    try:
        ipaddress.IPv4Address(build_stream_host_ip)
    except ValueError:
        errors.append(create_error_msg(build_stream_yml, "build_stream_host_ip",
                                       "Invalid IPv4 address format"))
        return errors

    # Validate that build_stream_host_ip matches an IP on an OIM ethernet interface
    # (i.e., it must be the OIM admin IP or OIM public IP)
    ethernet_ips = get_ethernet_interface_ips(logger)

    if not ethernet_ips:
        errors.append(create_error_msg(build_stream_yml, "build_stream_host_ip",
                                       msg.BUILD_STREAM_HOST_IP_NO_ETHERNET_IPS_MSG))
        return errors

    if build_stream_host_ip not in ethernet_ips:
        errors.append(create_error_msg(
            build_stream_yml, "build_stream_host_ip",
            msg.build_stream_host_ip_not_oim_ip_msg(build_stream_host_ip, ethernet_ips)
        ))

    # Validate aarch64_inventory_host_ip (c
    # Validate build_stream_port availability
    build_stream_port = data.get("build_stream_port")
    if build_stream_port:
        try:
            port_int = int(build_stream_port)
            if not (1 <= port_int <= 65535):
                raise ValueError
        except (TypeError, ValueError):
            errors.append(create_error_msg(
                build_stream_yml,
                "build_stream_port",
                msg.BUILD_STREAM_PORT_RANGE_MSG,
            ))
            return errors

        port_in_use = False
        try:
            with socket.create_connection((build_stream_host_ip, port_int), timeout=2):
                port_in_use = True
        except (OSError, ValueError):
            port_in_use = False

        if port_in_use:
            # Port is in use, check if it's build_stream by probing /health
            try:
                context = ssl._create_unverified_context()
                conn = client.HTTPSConnection(build_stream_host_ip, port_int, timeout=2, context=context)
                conn.request("GET", "/health")
                resp = conn.getresponse()
                conn.close()
                if resp.status not in [200, 401, 403, 404, 500]:
                    raise ValueError(f"Unexpected HTTP status {resp.status}")
            except Exception as exc:  # pylint: disable=broad-except
                errors.append(create_error_msg(
                    build_stream_yml,
                    "build_stream_port",
                    msg.BUILD_STREAM_PORT_INUSE_MSG.format(port=port_int, host_ip=build_stream_host_ip, detail=str(exc)),
                ))
                return errors

    # Validate aarch64_inventory_host_ip

    aarch64_inventory_host_ip = data.get("aarch64_inventory_host_ip")
    
    ### aarch64_inventory_host_ip check
    # Check if PXE mapping file contains aarch64 functional groups
    has_aarch64_groups = False
    try:
        pxe_mapping_path = os.path.join(omnia_base_dir, project_name, "pxe_mapping_file.csv")
        if os.path.exists(pxe_mapping_path):
            with open(pxe_mapping_path, 'r', encoding='utf-8') as f:
                # Skip header and check for aarch64 in functional group names
                for line in f:
                    if line.startswith('FUNCTIONAL_GROUP_NAME'):
                        continue
                    if 'aarch64' in line.lower():
                        has_aarch64_groups = True
                        break
        logger.debug("PXE mapping contains aarch64 groups: %s", has_aarch64_groups)
    except Exception as e:
        logger.warning("Failed to check PXE mapping file for aarch64 groups: %s", str(e))

    # If PXE mapping has aarch64 groups, require aarch64_inventory_host_ip
    if has_aarch64_groups:
        if not aarch64_inventory_host_ip or aarch64_inventory_host_ip in ["", None]:
            errors.append(create_error_msg(
                build_stream_yml, 
                "aarch64_inventory_host_ip",
                msg.AARCH64_INVENTORY_HOST_IP_REQUIRED_MSG
            ))
            return errors

    # If aarch64_inventory_host_ip is provided, validate it
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

        # Check aarch64 host IP reachability using socket (safer than subprocess)
        try:
            # Try to connect to SSH port which is usually open on inventory hosts
            ssh_port = 22  # SSH
            reachable = False
            
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(2)  # 2-second timeout
                    result = sock.connect_ex((str(aarch64_ip), ssh_port))
                    if result == 0:
                        reachable = True
                        logger.debug(f"aarch64 host {aarch64_ip} reachable on SSH port {ssh_port}")
            except (socket.timeout, socket.error):
                pass
            
            if not reachable:
                errors.append(create_error_msg(
                    build_stream_yml,
                    "aarch64_inventory_host_ip",
                    msg.AARCH64_INVENTORY_HOST_IP_NOT_REACHABLE_MSG.format(str(aarch64_ip))
                ))
        except Exception as e:
            logger.warning("Failed to check aarch64 host IP reachability: %s", str(e))
            errors.append(create_error_msg(
                build_stream_yml,
                "aarch64_inventory_host_ip",
                msg.AARCH64_INVENTORY_HOST_IP_REACHABILITY_CHECK_FAILED_MSG.format(str(aarch64_ip))
            ))

    # Validate build_stream_port
    build_stream_port = data.get("build_stream_port")

    if build_stream_port is not None:
        # Validate port range
        if not isinstance(build_stream_port, int) or not 1 <= build_stream_port <= 65535:
            errors.append(create_error_msg(
                build_stream_yml,
                "build_stream_port",
                "Port must be an integer between 1 and 65535"
            ))
        else:
            # Commenting out port availability check - temporarily disabled
            # Validate port availability (allows re-deployment with same port) - temporarily disabled
            # is_available, port_error = check_port_available(build_stream_port, admin_ip, logger)
            # if not is_available:
            #     errors.append(create_error_msg(
            #         build_stream_yml,
            #         "build_stream_port",
            #         port_error
            #     ))
            #     logger.error("Port %d is not available: %s", build_stream_port, port_error)
            pass


    return errors
