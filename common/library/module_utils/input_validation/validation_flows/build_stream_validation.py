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
import fcntl
import ipaddress
import os
import socket
import struct
import subprocess
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
    (type=1, has 'device' symlink, not a bridge) and socket ioctl
    to retrieve their IPv4 addresses. No external tools required.

    Args:
        logger: Logger instance

    Returns:
        list: List of IPv4 address strings from ethernet interfaces
    """
    ethernet_ips = []
    net_dir = '/sys/class/net'
    # SIOCGIFADDR ioctl to get interface address
    siocgifaddr = 0x8915

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

            # Get IPv4 address via ioctl
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    ip_bytes = fcntl.ioctl(
                        sock.fileno(),
                        siocgifaddr,
                        struct.pack('256s', iface.encode('utf-8')[:15])
                    )[20:24]
                    ip_addr = socket.inet_ntoa(ip_bytes)
                    ethernet_ips.append(ip_addr)
            except (IOError, OSError):
                # Interface exists but has no IPv4 address assigned
                logger.debug("No IPv4 address on interface %s", iface)
                continue

        logger.debug("Ethernet interface IPs found: %s", ethernet_ips)
    except OSError as e:
        logger.warning("Failed to get ethernet interface IPs: %s", str(e))
    return ethernet_ips


def is_port_used_by_build_stream(port, admin_ip, logger):
    """
    Check if the configured port is already in use by build_stream service.

    Build_stream listens on admin_ip:port. If we find the port listening on
    admin IP, it means build_stream is already deployed with this port.

    Args:
        port (int): The configured port from build_stream_config.yml
        admin_ip (str): The admin IP where build_stream listens
        logger: Logger instance

    Returns:
        bool: True if port is listening on admin IP (build_stream deployed)
    """
    try:
        result = subprocess.run(
            ['ss', '-tln', f'sport = :{port}'],
            capture_output=True, text=True, timeout=10, check=False
        )
        if result.returncode == 0 and admin_ip in result.stdout and 'LISTEN' in result.stdout:
            logger.info(
                "Port %d is listening on %s (build_stream re-deployment allowed)",
                port, admin_ip
            )
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("Failed to check port status: %s", str(e))
    return False


def check_port_available(port, admin_ip, logger):
    """
    Validate if port is available for build_stream deployment.

    Validation Logic:
    1. If port is listening on admin_ip → build_stream already deployed
       → PASS (re-deployment with same port allowed)
    2. If port is NOT listening on admin_ip → check if port is free
       → If free: PASS (new deployment)
       → If in use: FAIL (port conflict with another service)

    Args:
        port (int): The configured port from build_stream_config.yml
        admin_ip (str): The admin IP where build_stream listens
        logger: Logger instance

    Returns:
        tuple: (is_available: bool, error_message: str or None)
    """
    # Case 1: Port already used by build_stream → allow re-deployment
    if is_port_used_by_build_stream(port, admin_ip, logger):
        return True, None

    # Case 2: Check if port is free for new deployment
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', port))
            return True, None
    except OSError:
        return False, msg.build_stream_port_in_use_msg(port)
 
 
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
        else:
            logger.info(
                "build_stream_host_ip (%s) validated against OIM ethernet interface IPs",
                build_stream_host_ip
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
            # Validate port availability (allows re-deployment with same port)
            is_available, port_error = check_port_available(build_stream_port, admin_ip, logger)
            if not is_available:
                errors.append(create_error_msg(
                    build_stream_yml,
                    "build_stream_port",
                    port_error
                ))
                logger.error("Port %d is not available: %s", build_stream_port, port_error)

    return errors
