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
Discovery — OME (OpenManage Enterprise) Integration Functions.

Functions for connecting to OME and verifying discovery output against
live OME data. These tests require OME connectivity and valid credentials.

All verification functions return a dict with keys:
  success (bool), details (str), error (str), and optionally skipped (bool).
"""

import base64
import json
from typing import Any, Dict, List

from omnia_auto import (
    run_on_host,
)
from ..vars.common_vars import (
    OME_API_TIMEOUT,
    OME_SESSION_ENDPOINT,
    OME_GROUPS_ENDPOINT,
    OME_GROUP_DEVICES_ENDPOINT,
    PXE_MAPPING_SYMLINK,
    DEFAULT_FUNCTIONAL_GROUP,
    is_supported_functional_group,
)
from .discovery_func import _get_output_path, _read_pxe_mapping_raw


# Module-level cache for OME session
_ome_session_cache: Dict[str, Any] = {}

# OME session logout endpoint (matches src pattern)
OME_SESSION_LOGOUT_ENDPOINT: str = "/api/SessionService/Sessions('current')"


def clear_ome_cache() -> None:
    """Clear OME session cache (does not invalidate session on OME server)."""
    global _ome_session_cache
    _ome_session_cache.clear()


def close_ome_session(host) -> Dict[str, Any]:
    """Logout and invalidate the OME session.

    Follows the same pattern as src/discovery/plugins/modules/ome_server_inventory.py
    to properly invalidate the session on the OME server.

    Args:
        host: Testinfra host object

    Returns:
        Dict with success, details, error
    """
    global _ome_session_cache

    result = {
        "success": True,
        "details": "",
        "error": "",
    }

    token = _ome_session_cache.get("token")
    ome_ip = _ome_session_cache.get("ome_ip")

    if not token or not ome_ip:
        result["details"] = "No active OME session to close"
        clear_ome_cache()
        return result

    # Call DELETE on session endpoint to invalidate token
    resp = _ome_api_request(
        host, ome_ip, OME_SESSION_LOGOUT_ENDPOINT,
        method="DELETE", auth_token=token
    )

    # Clear cache regardless of response (session may have already expired)
    clear_ome_cache()

    if resp["success"] or resp["status_code"] in [200, 204, 401]:
        # 401 means session already expired - that's fine
        result["details"] = "OME session closed successfully"
    else:
        # Log but don't fail - session cleanup is best-effort
        result["details"] = f"OME session logout returned {resp['status_code']}"

    return result


def _ome_api_request(
    host,
    ome_ip: str,
    endpoint: str,
    method: str = "GET",
    data: Dict = None,
    auth_token: str = None,
) -> Dict[str, Any]:
    """Make HTTP request to OME REST API via curl.

    Args:
        host: Testinfra host object
        ome_ip: OME IP address
        endpoint: API endpoint
        method: HTTP method (GET, POST)
        data: JSON data for POST
        auth_token: X-Auth-Token for authenticated requests

    Returns:
        Dict with success, status_code, response, headers, error
    """
    result = {
        "success": False,
        "status_code": 0,
        "response": {},
        "headers": {},
        "error": "",
    }

    url = f"https://{ome_ip}{endpoint}"

    # Build curl command
    curl_parts = [
        "curl", "-s", "-k",
        "-D", "/tmp/ome_headers.txt",  # nosec: B108 - temp file cleaned up after use
        "-w", "'\\n%{http_code}'",
        "-X", method,
        f"--connect-timeout {OME_API_TIMEOUT}",
    ]

    if auth_token:
        curl_parts.append(f"-H 'X-Auth-Token: {auth_token}'")

    curl_parts.append(f"'{url}'")

    if method == "POST" and data:
        curl_parts.insert(3, "-H 'Content-Type: application/json'")
        json_data = json.dumps(data)
        b64_data = base64.b64encode(json_data.encode()).decode()
        curl_cmd = " ".join(curl_parts)
        cmd_str = (
            f"bash -c \"echo '{b64_data}' | base64 -d > /tmp/ome_post.json "  # nosec: B108 - temp file cleaned up after use
            f"&& {curl_cmd} -d @/tmp/ome_post.json\""
        )
    else:
        cmd_str = " ".join(curl_parts)

    cmd = run_on_host(host, cmd_str)
    if cmd.rc != 0:
        result["error"] = f"curl failed: {cmd.stderr}"
        return result

    lines = cmd.stdout.strip().split("\n")
    if not lines:
        result["error"] = "Empty response from OME"
        return result

    try:
        result["status_code"] = int(lines[-1])
    except ValueError:
        result["error"] = f"Invalid status code: {lines[-1]}"
        return result

    body = "\n".join(lines[:-1])
    if body:
        try:
            result["response"] = json.loads(body)
        except json.JSONDecodeError:
            result["response"] = {}

    # Read headers
    headers_cmd = run_on_host(host, "cat /tmp/ome_headers.txt 2>/dev/null")
    if headers_cmd.rc == 0:
        for line in headers_cmd.stdout.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                result["headers"][key.strip()] = val.strip()

    # Clean up temp files
    run_on_host(host, "rm -f /tmp/ome_headers.txt /tmp/ome_post.json 2>/dev/null")  # nosec: B108

    if 200 <= result["status_code"] < 300:
        result["success"] = True
    else:
        err_msg = result["response"].get("error", {}).get("message", "Unknown")
        result["error"] = f"HTTP {result['status_code']}: {err_msg}"

    return result


def _get_ome_config(host) -> Dict[str, Any]:
    """Get OME configuration from discovery input files.

    Reads OME IP from discovery_config.yml and credentials from
    discovery_credentials.yml (decrypted using the vault key).

    Args:
        host: Testinfra host object

    Returns:
        Dict with ome_ip, ome_username, ome_password, or error
    """
    from ..vars.common_vars import (
        DOMAIN_NAME,
        ENV_OMNIA_DATA_PATH,
        ENV_DISCOVERY_DATA_PATH,
        ENV_OMNIA_PROJECT_NAME,
        DISCOVERY_CONFIG_FILE,
        CREDENTIALS_FILE_NAME,
        CREDENTIALS_KEY_NAME,
    )
    from omnia_auto import (
        read_remote_env,
        resolve_domain_data_path,
    )

    result = {
        "success": False,
        "ome_ip": "",
        "ome_username": "",
        "ome_password": "",
        "error": "",
    }

    try:
        # Get the input path
        domain_data_path = resolve_domain_data_path(
            host,
            DOMAIN_NAME,
            ENV_OMNIA_DATA_PATH,
            domain_data_path_var=ENV_DISCOVERY_DATA_PATH,
        )
        project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
        input_path = f"{domain_data_path}/input/{project}"

        # Read discovery_config.yml to get ome_ip
        config_path = f"{input_path}/{DISCOVERY_CONFIG_FILE}"
        cmd = run_on_host(host, f"cat {config_path} 2>/dev/null")
        if cmd.rc != 0:
            result["error"] = f"Cannot read {DISCOVERY_CONFIG_FILE}"
            return result

        # Parse YAML to get ome_ip
        import yaml
        try:
            config = yaml.safe_load(cmd.stdout)
            result["ome_ip"] = config.get("ome_ip", "")
        except yaml.YAMLError as e:
            result["error"] = f"Failed to parse {DISCOVERY_CONFIG_FILE}: {e}"
            return result

        if not result["ome_ip"]:
            result["error"] = "ome_ip not configured in discovery_config.yml"
            return result

        # Read discovery_credentials.yml (decrypt with vault key)
        creds_path = f"{input_path}/{CREDENTIALS_FILE_NAME}"
        key_path = f"{input_path}/{CREDENTIALS_KEY_NAME}"

        # Check if credentials file exists
        check_cmd = run_on_host(host, f"test -f {creds_path} && echo exists")
        if check_cmd.rc != 0 or "exists" not in check_cmd.stdout:
            result["error"] = f"Credentials file not found: {creds_path}"
            return result

        # Check if key file exists
        check_key_cmd = run_on_host(host, f"test -f {key_path} && echo exists")
        if check_key_cmd.rc != 0 or "exists" not in check_key_cmd.stdout:
            result["error"] = f"Credentials key not found: {key_path}"
            return result

        # Decrypt and read credentials
        decrypt_cmd = run_on_host(
            host,
            f"ansible-vault view {creds_path} --vault-password-file {key_path} 2>/dev/null"
        )
        if decrypt_cmd.rc != 0:
            result["error"] = f"Failed to decrypt credentials: {decrypt_cmd.stderr}"
            return result

        try:
            creds = yaml.safe_load(decrypt_cmd.stdout)
            result["ome_username"] = creds.get("ome_username", "")
            result["ome_password"] = creds.get("ome_password", "")
        except yaml.YAMLError as e:
            result["error"] = f"Failed to parse credentials: {e}"
            return result

        if not result["ome_username"] or not result["ome_password"]:
            result["error"] = "OME credentials (ome_username/ome_password) not set"
            return result

        result["success"] = True
    except Exception as e:
        result["error"] = f"Failed to load OME config: {e}"

    return result


def get_ome_session(host) -> Dict[str, Any]:
    """Create authenticated session with OME.

    Args:
        host: Testinfra host object

    Returns:
        Dict with success, token, ome_ip, error
    """
    global _ome_session_cache

    result = {
        "success": False,
        "token": "",
        "ome_ip": "",
        "error": "",
    }

    if _ome_session_cache.get("token"):
        result["token"] = _ome_session_cache["token"]
        result["ome_ip"] = _ome_session_cache["ome_ip"]
        result["success"] = True
        return result

    ome_config = _get_ome_config(host)
    if not ome_config["success"]:
        result["error"] = ome_config["error"]
        return result

    ome_ip = ome_config["ome_ip"]
    result["ome_ip"] = ome_ip

    session_data = {
        "UserName": ome_config["ome_username"],
        "Password": ome_config["ome_password"],
        "SessionType": "API",
    }

    resp = _ome_api_request(
        host, ome_ip, OME_SESSION_ENDPOINT, method="POST", data=session_data
    )
    if not resp["success"]:
        result["error"] = f"Failed to create OME session: {resp['error']}"
        return result

    token = resp["headers"].get("X-Auth-Token", "")
    if not token:
        result["error"] = "No X-Auth-Token in OME response headers"
        return result

    _ome_session_cache["token"] = token
    _ome_session_cache["ome_ip"] = ome_ip

    result["token"] = token
    result["success"] = True
    return result


def get_ome_static_groups(host) -> Dict[str, Any]:
    """Get static groups from OME (under Custom Groups > Static Groups).

    Args:
        host: Testinfra host object

    Returns:
        Dict with success, groups (list of name, id), error
    """
    result = {
        "success": False,
        "groups": [],
        "error": "",
    }

    session = get_ome_session(host)
    if not session["success"]:
        result["error"] = session["error"]
        return result

    resp = _ome_api_request(
        host,
        session["ome_ip"],
        OME_GROUPS_ENDPOINT,
        auth_token=session["token"]
    )

    if not resp["success"]:
        result["error"] = f"Failed to get OME groups: {resp['error']}"
        return result

    # Find Static Groups parent ID
    all_groups = resp["response"].get("value", [])
    static_groups_id = None
    for g in all_groups:
        if g.get("Name") == "Static Groups":
            static_groups_id = g.get("Id")
            break

    if not static_groups_id:
        result["error"] = "Static Groups parent not found in OME"
        return result

    # Get subgroups of Static Groups
    resp2 = _ome_api_request(
        host,
        session["ome_ip"],
        f"/api/GroupService/Groups({static_groups_id})/SubGroups",
        auth_token=session["token"]
    )

    if not resp2["success"]:
        result["error"] = f"Failed to get Static Groups subgroups: {resp2['error']}"
        return result

    subgroups = resp2["response"].get("value", [])
    for g in subgroups:
        result["groups"].append({
            "name": g.get("Name", ""),
            "id": g.get("Id", 0),
            "device_count": g.get("MembershipTypeId", 0) if g.get("MembershipTypeId") else len(g.get("Devices", [])),
        })

    # Get actual device count for each group
    for group in result["groups"]:
        devices_resp = _ome_api_request(
            host,
            session["ome_ip"],
            f"/api/GroupService/Groups({group['id']})/Devices",
            auth_token=session["token"]
        )
        if devices_resp["success"]:
            devices = devices_resp["response"].get("value", [])
            group["device_count"] = len(devices)

    result["success"] = True
    return result


def get_ome_device_details(host, service_tag: str) -> Dict[str, Any]:
    """Get device details from OME by service tag.

    Returns first_nic_mac (first active non-iDRAC NIC) and ib_nic_name.

    Args:
        host: Testinfra host object
        service_tag: Device service tag

    Returns:
        Dict with success, device_id, first_nic_mac, first_nic_name,
        ib_nic_name, ib_nic_status, ib_nic_exists, error
    """
    result = {
        "success": False,
        "device_id": 0,
        "first_nic_mac": "",
        "first_nic_name": "",
        "ib_nic_name": "",
        "ib_nic_status": "",
        "ib_nic_exists": False,
        "error": "",
    }

    session = get_ome_session(host)
    if not session["success"]:
        result["error"] = session["error"]
        return result

    # Find device by service tag
    endpoint = (
        f"/api/DeviceService/Devices?"
        f"%24filter=Identifier%20eq%20%27{service_tag}%27"
    )
    resp = _ome_api_request(
        host,
        session["ome_ip"],
        endpoint,
        auth_token=session["token"]
    )

    if not resp["success"]:
        result["error"] = f"Failed to find device: {resp['error']}"
        return result

    devices = resp["response"].get("value", [])
    if not devices:
        result["error"] = f"Device '{service_tag}' not found in OME"
        return result

    device = devices[0]
    device_id = device.get("Id", 0)
    result["device_id"] = device_id

    # Get NIC inventory
    nic_endpoint = (
        f"/api/DeviceService/Devices({device_id})/"
        f"InventoryDetails(%27serverNetworkInterfaces%27)"
    )
    nic_resp = _ome_api_request(
        host,
        session["ome_ip"],
        nic_endpoint,
        auth_token=session["token"]
    )

    if not nic_resp["success"]:
        result["error"] = f"Failed to get device inventory: {nic_resp['error']}"
        return result

    nic_info_list = nic_resp["response"].get("InventoryInfo", [])

    # Find first non-iDRAC NIC with LinkStatus "Up"
    fallback_nic_name = ""
    fallback_nic_mac = ""
    all_nic_macs = []  # Track all NIC MACs for detailed error reporting

    for nic in nic_info_list:
        nic_id = nic.get("NicId", "")
        if "iDRAC" in nic_id.upper():
            continue

        ports = nic.get("Ports", [])
        for port in ports:
            partitions = port.get("Partitions", [])
            if not partitions:
                continue
            mac = partitions[0].get("CurrentMacAddress", "")
            if not mac:
                continue

            # Track all NIC MACs for detailed reporting
            link_status = (port.get("LinkStatus") or "").strip()
            all_nic_macs.append({
                "nic_id": nic_id,
                "mac": mac,
                "link_status": link_status,
            })

            if not fallback_nic_mac:
                fallback_nic_name = nic_id
                fallback_nic_mac = mac

            if link_status.upper() == "UP":
                result["first_nic_name"] = nic_id
                result["first_nic_mac"] = mac
                break

        if result["first_nic_mac"]:
            break

    if not result["first_nic_mac"] and fallback_nic_mac:
        result["first_nic_name"] = fallback_nic_name
        result["first_nic_mac"] = fallback_nic_mac

    # Store all NIC MACs for detailed error reporting
    result["all_nic_macs"] = all_nic_macs

    # Get InfiniBand NIC
    for nic in nic_info_list:
        nic_id = nic.get("NicId", "")
        if "infiniband" not in nic_id.lower():
            continue
        result["ib_nic_exists"] = True
        for port in nic.get("Ports", []):
            link_status = (port.get("LinkStatus") or "").strip()
            port_id = port.get("PortId", "")
            nic_name = port_id if port_id else nic_id

            if link_status.upper() == "UP":
                result["ib_nic_name"] = nic_name
                result["ib_nic_status"] = "Up"
                break
            elif link_status.upper() == "DOWN" and not result["ib_nic_name"]:
                result["ib_nic_status"] = "Down"

        if result["ib_nic_name"]:
            break

    result["success"] = True
    return result


def check_ome_static_groups_match(host) -> Dict[str, Any]:
    """Verify OME static groups match PXE mapping functional groups.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, matched_groups, unmatched_pxe,
                       unmatched_ome, details, error, skipped.
    """
    result = {
        "success": False,
        "matched_groups": [],
        "unmatched_pxe": [],
        "unmatched_ome": [],
        "details": "",
        "error": "",
        "skipped": False,
    }

    # Check if OME is configured
    ome_config = _get_ome_config(host)
    if not ome_config["success"]:
        result["skipped"] = True
        result["details"] = "OME not configured - skipping OME validation"
        result["success"] = True
        return result

    # Get PXE mapping functional groups
    mapping = _read_pxe_mapping_raw(host)
    if not mapping["success"]:
        result["error"] = mapping["error"]
        return result

    try:
        fg_idx = mapping["headers"].index("FUNCTIONAL_GROUP_NAME")
    except ValueError:
        result["error"] = "FUNCTIONAL_GROUP_NAME column not found"
        return result

    pxe_groups = set()
    for row in mapping["rows"]:
        if len(row) > fg_idx and row[fg_idx]:
            pxe_groups.add(row[fg_idx])

    # Get OME static groups
    ome_groups_result = get_ome_static_groups(host)
    if not ome_groups_result["success"]:
        result["error"] = ome_groups_result["error"]
        return result

    # Get OME groups with their device counts
    ome_groups = set(g["name"] for g in ome_groups_result["groups"])
    ome_groups_with_devices = set(
        g["name"] for g in ome_groups_result["groups"]
        if g.get("device_count", 0) > 0
    )

    # Groups in PXE that match OME groups WITH devices assigned
    result["matched_groups"] = sorted(list(pxe_groups & ome_groups_with_devices))
    # Groups in PXE not in OME at all
    result["unmatched_pxe"] = sorted(list(pxe_groups - ome_groups))
    # Groups in OME not used in PXE
    result["unmatched_ome"] = sorted(list(ome_groups - pxe_groups))

    # Groups that exist in OME but have no devices - these are used as defaults
    # (the group name exists in OME but devices fell back to it because they
    # weren't assigned to any group)
    ome_empty_groups_used = pxe_groups & (ome_groups - ome_groups_with_devices)

    # Check if unmatched PXE groups are valid default groups
    default_groups = []
    invalid_groups = []
    # Include both: groups not in OME + empty OME groups used as defaults
    potential_defaults = result["unmatched_pxe"] + list(ome_empty_groups_used)
    for group in potential_defaults:
        if is_supported_functional_group(group):
            if group not in default_groups:
                default_groups.append(group)
        else:
            if group not in invalid_groups:
                invalid_groups.append(group)

    # Count devices using default groups (not assigned in OME)
    default_group_count = 0
    for row in mapping["rows"]:
        if len(row) > fg_idx and row[fg_idx] in default_groups:
            default_group_count += 1

    # Count devices in matched OME groups (actually assigned in OME)
    matched_device_count = 0
    for row in mapping["rows"]:
        if len(row) > fg_idx and row[fg_idx] in result["matched_groups"]:
            matched_device_count += 1

    # Store counts for detailed reporting
    result["matched_device_count"] = matched_device_count
    result["default_device_count"] = default_group_count
    result["default_groups"] = sorted(default_groups)

    if invalid_groups:
        result["details"] = (
            f"Invalid groups not in OME: {', '.join(invalid_groups)}"
        )
        result["error"] = result["details"]
    elif default_groups:
        result["details"] = (
            f"{len(result['matched_groups'])} OME groups ({matched_device_count} devices); "
            f"{len(default_groups)} default groups ({default_group_count} devices): "
            f"{', '.join(sorted(default_groups))}"
        )
        result["success"] = True
    else:
        result["success"] = True
        result["details"] = (
            f"{len(result['matched_groups'])} OME groups ({matched_device_count} devices); "
            f"0 devices using default groups"
        )

    return result


def check_ome_unassigned_devices(host) -> Dict[str, Any]:
    """Verify OME devices without static group assignment.

    These devices will get the default functional group during discovery.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, unassigned_count, unassigned_devices,
                       details, error, skipped.
    """
    result = {
        "success": False,
        "unassigned_count": 0,
        "unassigned_devices": [],
        "details": "",
        "error": "",
        "skipped": False,
    }

    # Check if OME is configured
    ome_config = _get_ome_config(host)
    if not ome_config["success"]:
        result["skipped"] = True
        result["details"] = "OME not configured - skipping OME validation"
        result["success"] = True
        return result

    session = get_ome_session(host)
    if not session["success"]:
        result["error"] = session["error"]
        return result

    # Get all devices
    resp = _ome_api_request(
        host,
        session["ome_ip"],
        "/api/DeviceService/Devices?%24filter=Type%20eq%201000",
        auth_token=session["token"]
    )

    if not resp["success"]:
        result["error"] = f"Failed to get OME devices: {resp['error']}"
        return result

    all_devices = resp["response"].get("value", [])

    # Get static groups and their device IDs
    static_groups = get_ome_static_groups(host)
    if not static_groups["success"]:
        result["error"] = static_groups["error"]
        return result

    assigned_device_ids = set()
    for group in static_groups["groups"]:
        group_resp = _ome_api_request(
            host,
            session["ome_ip"],
            f"/api/GroupService/Groups({group['id']})/Devices",
            auth_token=session["token"]
        )
        if group_resp["success"]:
            for device in group_resp["response"].get("value", []):
                assigned_device_ids.add(device.get("Id", 0))

    # Find unassigned devices
    for device in all_devices:
        if device.get("Id", 0) not in assigned_device_ids:
            result["unassigned_devices"].append({
                "id": device.get("Id", 0),
                "name": device.get("DeviceName", ""),
                "identifier": device.get("Identifier", ""),
            })

    result["unassigned_count"] = len(result["unassigned_devices"])
    result["success"] = True
    result["details"] = (
        f"{result['unassigned_count']} devices without static group assignment"
    )

    return result


def check_admin_mac_validation(host) -> Dict[str, Any]:
    """Verify ADMIN_MAC in PXE mapping matches OME first active non-iDRAC NIC.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, valid_count, invalid_rows, details, error, skipped.
    """
    result = {
        "success": False,
        "valid_count": 0,
        "invalid_rows": [],
        "details": "",
        "error": "",
        "skipped": False,
    }

    # Check if OME is configured
    ome_config = _get_ome_config(host)
    if not ome_config["success"]:
        result["skipped"] = True
        result["details"] = "OME not configured - skipping OME validation"
        result["success"] = True
        return result

    mapping = _read_pxe_mapping_raw(host)
    if not mapping["success"]:
        result["error"] = mapping["error"]
        return result

    headers = mapping["headers"]
    try:
        st_idx = headers.index("SERVICE_TAG")
        mac_idx = headers.index("ADMIN_MAC")
        hostname_idx = headers.index("HOSTNAME")
    except ValueError as e:
        result["error"] = f"Required column not found: {e}"
        return result

    # Validate a sample of rows (max 10 to avoid API rate limits)
    sample_rows = mapping["rows"][:10]

    for row in sample_rows:
        if len(row) <= max(st_idx, mac_idx, hostname_idx):
            continue

        service_tag = row[st_idx]
        pxe_mac = row[mac_idx].upper().replace("-", ":")
        hostname = row[hostname_idx]

        if not service_tag or not pxe_mac:
            continue

        ome_details = get_ome_device_details(host, service_tag)
        if not ome_details["success"]:
            result["invalid_rows"].append({
                "hostname": hostname,
                "service_tag": service_tag,
                "pxe_mac": pxe_mac,
                "reason": ome_details["error"],
            })
            continue

        ome_mac = ome_details["first_nic_mac"].upper().replace("-", ":")
        if pxe_mac != ome_mac:
            result["invalid_rows"].append({
                "hostname": hostname,
                "service_tag": service_tag,
                "pxe_mac": pxe_mac,
                "ome_mac": ome_mac,
            })
        else:
            result["valid_count"] += 1

    if result["invalid_rows"]:
        # Build concise error message
        mac_mismatches = [
            f"{row['hostname']}: PXE={row['pxe_mac']} OME={row['ome_mac']}"
            for row in result["invalid_rows"]
        ]
        result["details"] = (
            f"{len(result['invalid_rows'])} MAC mismatches"
        )
        result["error"] = result["details"]
        result["mac_mismatches"] = mac_mismatches
    else:
        result["success"] = True
        result["details"] = (
            f"All {result['valid_count']} sampled rows valid"
        )

    return result


def check_ib_nic_name_validation(host) -> Dict[str, Any]:
    """Verify IB_NIC_NAME in PXE mapping matches OME first active InfiniBand NIC.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, valid_count, invalid_rows, details, error, skipped.
    """
    result = {
        "success": False,
        "valid_count": 0,
        "invalid_rows": [],
        "details": "",
        "error": "",
        "skipped": False,
    }

    # Check if OME is configured
    ome_config = _get_ome_config(host)
    if not ome_config["success"]:
        result["skipped"] = True
        result["details"] = "OME not configured - skipping OME validation"
        result["success"] = True
        return result

    mapping = _read_pxe_mapping_raw(host)
    if not mapping["success"]:
        result["error"] = mapping["error"]
        return result

    headers = mapping["headers"]

    # IB_NIC_NAME is optional
    if "IB_NIC_NAME" not in headers:
        result["success"] = True
        result["details"] = "IB_NIC_NAME column not present (optional)"
        return result

    try:
        st_idx = headers.index("SERVICE_TAG")
        ib_idx = headers.index("IB_NIC_NAME")
        hostname_idx = headers.index("HOSTNAME")
    except ValueError as e:
        result["error"] = f"Required column not found: {e}"
        return result

    # Validate a sample of rows with IB_NIC_NAME (max 10)
    sample_count = 0
    for row in mapping["rows"]:
        if sample_count >= 10:
            break

        if len(row) <= max(st_idx, ib_idx, hostname_idx):
            continue

        service_tag = row[st_idx]
        pxe_ib_nic = row[ib_idx]
        hostname = row[hostname_idx]

        if not service_tag or not pxe_ib_nic:
            continue

        sample_count += 1

        ome_details = get_ome_device_details(host, service_tag)
        if not ome_details["success"]:
            result["invalid_rows"].append({
                "hostname": hostname,
                "service_tag": service_tag,
                "pxe_ib_nic": pxe_ib_nic,
                "reason": ome_details["error"],
            })
            continue

        if not ome_details["ib_nic_exists"]:
            result["invalid_rows"].append({
                "hostname": hostname,
                "service_tag": service_tag,
                "pxe_ib_nic": pxe_ib_nic,
                "reason": "No InfiniBand NIC found in OME",
            })
            continue

        ome_ib_nic = ome_details["ib_nic_name"]
        if pxe_ib_nic != ome_ib_nic and ome_ib_nic:
            result["invalid_rows"].append({
                "hostname": hostname,
                "service_tag": service_tag,
                "pxe_ib_nic": pxe_ib_nic,
                "ome_ib_nic": ome_ib_nic,
                "reason": f"IB NIC mismatch: PXE={pxe_ib_nic}, OME={ome_ib_nic}",
            })
        else:
            result["valid_count"] += 1

    if result["invalid_rows"]:
        result["details"] = (
            f"{len(result['invalid_rows'])} rows have IB_NIC_NAME validation issues"
        )
        result["error"] = result["details"]
    else:
        result["success"] = True
        result["details"] = (
            f"All {result['valid_count']} sampled rows have valid IB_NIC_NAME"
        )

    return result
