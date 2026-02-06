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
# pylint: disable=import-error,no-name-in-module
import requests
import socket
import ssl
from requests.auth import HTTPBasicAuth
from ansible.module_utils.local_repo.common_functions import is_file_exists

def is_https(host, timeout=1):
    ip, port = host.rsplit(":", 1)
    port = int(port)

    # Don't verify server cert; just see if TLS works
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        with socket.create_connection((ip, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=ip):
                return True
    except ssl.SSLError:
        return False
    except Exception:
        return False

def validate_user_registry(user_registry):
    """
    Validates a list of user registry entries with connectivity and credential check.
    Args:
        user_registry (list): List of user registry dictionaries.
    Returns:
        tuple: (bool, str) indicating overall validity and error message if invalid.
    """
    if not isinstance(user_registry, list):
        return False, "user_registry must be a list."

    for idx, item in enumerate(user_registry):
        if not isinstance(item, dict):
            return False, f"Entry at index {idx} must be a dictionary."

        host = item.get('host')
        if not host:
            return False, f"Missing or empty 'host' in entry at index {idx}: {item}"
        https = is_https(host)

        cert_path = (item.get("cert_path") or "").strip()
        key_path  = (item.get("key_path")  or "").strip()

        if https and (not cert_path or not key_path):
            return False, f"{host} is an HTTPS registry and requires cert_path and key_path. Please provide cert_path and key_path in local_repo_config.yml under user_registry section"

    return True, ""

        # requires_auth = item.get('requires_auth', False)

        # # Check basic username/password presence
        # if requires_auth:
        #     if not item.get('username') or not item.get('password'):
        #         return False, (
        #             f"'requires_auth' is true but 'username' or 'password' is missing or empty "
        #             f"in entry for (host: {host})"
        #         )

        #     cert_path = item.get('cert_path')
        #     key_path = item.get('key_path')

    #         if bool(cert_path) != bool(key_path):
    #             return False, (
    #                 f"If authentication is enabled, both 'cert_path' and 'key_path' must be present "
    #                 f"or both omitted in entry for (host: {host})"
    #             )
    #         try:
    #             url = f"https://{host}/api/v2.0/users/current"
    #             response = requests.get(
    #                 url,
    #                 auth=HTTPBasicAuth(item['username'], item['password']),
    #                 verify=True  # Set to True if using valid SSL certs
    #             )

    #             if response.status_code == 401:
    #                 return False, f"Invalid credentials for host: {host}"
    #             elif response.status_code != 200:
    #                 return False, f"Unexpected status {response.status_code} while validating host: {host}"

    #         except requests.exceptions.RequestException as e:
    #             return False, f"Failed to connect to {host}: {str(e)}"

    # return True, ""

def tcp_ping(host, timeout=1):
    """
    Check if a host:port is reachable via TCP.
    
    Args:
        host (str): User registry host with port
        timeout (int): Timeout in seconds
    Returns:
        bool: True if reachable, False otherwise
    """
    try:
        if ":" in host:
            hostname, port = host.split(":")
            port = int(port)
        else:
            hostname = host
            port = 443

        with socket.create_connection((hostname, port), timeout=timeout):
            return True
    except Exception:
        return False

def check_reachability(user_registry, timeout=1):
    """
    Check reachability of hosts in a user registry.
    
    Args:
        user_registry (list): List of dicts, each with a 'host' key
        timeout (int): TCP connection timeout in seconds
    Returns:
        tuple: (reachable_hosts, unreachable_hosts)
    """
    reachable, unreachable = [], []
    for item in user_registry:
        host = item['host']
        if tcp_ping(host, timeout):
            reachable.append(host)
        else:
            unreachable.append(host)
    return reachable, unreachable

def find_invalid_cert_paths(user_registry):
    """
    Finds invalid certificate/key path configurations in the user registry.

    Rules:
    - If cert_path is provided, key_path must also be provided, and vice versa.
    - If either path is provided, the corresponding file must exist.

    Args:
        user_registry (list): List of dictionaries representing user registry entries.

    Returns:
        list: A list of error strings describing invalid entries.
    """
    invalid_entries = []

    for idx, item in enumerate(user_registry):
        cert_path = item.get('cert_path')
        key_path = item.get('key_path')
        name_or_host = item.get('name') or item.get('host') or f"entry {idx}"

        # If only one of cert or key is provided
        if bool(cert_path) != bool(key_path):
            invalid_entries.append(
                f"{name_or_host}: Both 'cert_path' and 'key_path' must be provided together or not at all."
            )
            continue

        # If both are provided, validate file existence
        if cert_path and not is_file_exists(cert_path):
            invalid_entries.append(f"{name_or_host}: cert_path '{cert_path}' does not exist.")

        if key_path and not is_file_exists(key_path):
            invalid_entries.append(f"{name_or_host}: key_path '{key_path}' does not exist.")

    return invalid_entries
