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
OME — Module-Specific Verification Functions.

Handles:
  - OME Kafka forwarder connectivity status via REST API
  - OME DataForwardingService forwarder details

All shell commands are referenced from ``CMDS`` in ``common_vars.py``.
"""

import json

from omnia_auto import run_on_host

from library.vars.common_vars import CMDS


def verify_ome_kafka_connectivity(host, ome_ip, ome_user, ome_password,
                                  forwarder_id=10):
    """Check OME Kafka forwarder connectivity status via REST API.

    Uses: GET /api/DataForwardingService/Forwarders({id})/ConnectivityStatus

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address (from test_config.yml).
        ome_user: OME admin username (from test_creds.yml).
        ome_password: OME admin password (from test_creds.yml).
        forwarder_id: Forwarder ID (default: 10 for Kafka).

    Returns:
        dict with keys: success, status, time_last_connected,
        forwarder_name, forwarder_enabled, error.
    """
    # First get forwarder details
    forwarder_cmd = CMDS["ome_get_forwarder"].format(
        user=ome_user, password=ome_password,
        ome_ip=ome_ip, forwarder_id=forwarder_id,
    )
    result = run_on_host(host, forwarder_cmd)
    forwarder_name = ""
    forwarder_enabled = False

    if result.rc == 0 and result.stdout.strip():
        try:
            fwd = json.loads(result.stdout)
            if "error" in fwd:
                error_msg = fwd["error"].get("message", "Unknown error")
                return {
                    "success": False,
                    "status": "Unknown",
                    "error": f"API error: {error_msg}",
                }
            forwarder_name = fwd.get("Name", "")
            forwarder_enabled = fwd.get("Enabled", False)
        except json.JSONDecodeError:
            pass

    # Get connectivity status
    status_cmd = CMDS["ome_get_forwarder_status"].format(
        user=ome_user, password=ome_password,
        ome_ip=ome_ip, forwarder_id=forwarder_id,
    )
    result = run_on_host(host, status_cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "status": "Unreachable",
            "forwarder_name": forwarder_name,
            "forwarder_enabled": forwarder_enabled,
            "error": f"Cannot reach OME at {ome_ip}",
        }

    try:
        data = json.loads(result.stdout)
        if "error" in data:
            error_msg = data["error"].get("message", "Authentication failed")
            return {
                "success": False,
                "status": "AuthError",
                "forwarder_name": forwarder_name,
                "forwarder_enabled": forwarder_enabled,
                "error": error_msg,
            }

        status = data.get("Status", "Unknown")
        time_connected = data.get("TimeLastConnected", "")
        connected = status == "Connected"

        return {
            "success": connected,
            "status": status,
            "time_last_connected": time_connected,
            "forwarder_name": forwarder_name,
            "forwarder_enabled": forwarder_enabled,
            "error": "" if connected else f"Kafka status: {status}",
        }
    except json.JSONDecodeError:
        return {
            "success": False,
            "status": "ParseError",
            "error": "Invalid JSON from OME API",
        }


def get_ome_forwarders(host, ome_ip, ome_user, ome_password):
    """List all OME DataForwardingService forwarders.

    Uses: GET /api/DataForwardingService/Forwarders

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address (from test_config.yml).
        ome_user: OME admin username (from test_creds.yml).
        ome_password: OME admin password (from test_creds.yml).

    Returns:
        dict with keys: success, forwarders (list), error.
    """
    cmd = CMDS["ome_get_forwarders_list"].format(
        user=ome_user, password=ome_password, ome_ip=ome_ip,
    )
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {"success": False, "forwarders": [], "error": "Cannot reach OME"}

    try:
        data = json.loads(result.stdout)
        if "error" in data:
            return {
                "success": False,
                "forwarders": [],
                "error": data["error"].get("message", "Auth error"),
            }
        forwarders = data.get("value", [])
        return {"success": True, "forwarders": forwarders, "error": ""}
    except json.JSONDecodeError:
        return {"success": False, "forwarders": [], "error": "Invalid JSON"}
