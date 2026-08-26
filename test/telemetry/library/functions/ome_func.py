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
  - External Kafka TLS certificate extraction and verification
  - PFX certificate conversion for OME mTLS
  - OME Kafka forwarder connectivity status via REST API
  - OME DataForwardingService forwarder details

All shell commands are referenced from ``CMDS`` in ``common_vars.py``.
"""

import json

from omnia_auto import run_on_host

from ..vars.common_vars import (
    CMDS,
    TELEMETRY_NAMESPACE,
    PLAYBOOK_WORKDIR,
    PLAYBOOK_ENTRY_POINT,
    OME_KAFKA_USER,
    OME_KAFKA_CERT_SUBDIR,
    OME_KAFKA_CERT_FILES,
)
from .telemetry_func import run_on_kube_vip, get_output_path


def _get_cert_dir(host):
    """Resolve the external_kafka cert directory on the OIM.

    Returns:
        str: e.g. /opt/omnia/telemetry/output/project_default/external_kafka
    """
    return f"{get_output_path(host)}/{OME_KAFKA_CERT_SUBDIR}"


def verify_ome_kafka_connectivity(host, ome_ip, ome_user,
                                  ome_password, forwarder_id=10):
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
                error_msg = fwd["error"].get(
                    "message", "Unknown error"
                )
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
            error_msg = data["error"].get(
                "message", "Authentication failed"
            )
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
            "error": (
                "" if connected else f"Kafka status: {status}"
            ),
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
        return {
            "success": False,
            "forwarders": [],
            "error": "Cannot reach OME",
        }

    try:
        data = json.loads(result.stdout)
        if "error" in data:
            return {
                "success": False,
                "forwarders": [],
                "error": data["error"].get("message", "Auth error"),
            }
        forwarders = data.get("value", [])
        return {
            "success": True,
            "forwarders": forwarders,
            "error": "",
        }
    except json.JSONDecodeError:
        return {
            "success": False,
            "forwarders": [],
            "error": "Invalid JSON",
        }


# -------------------------------------------------------------------------
# External Kafka TLS certificates (for OME mTLS integration)
# -------------------------------------------------------------------------

def run_external_kafka_playbook(host):
    """Run the external_kafka_connect playbook to extract TLS certs.

    Runs: ansible-playbook telemetry.yml --tags external_kafka

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, output, error.
    """
    cmd = CMDS["ansible_playbook"].format(
        workdir=PLAYBOOK_WORKDIR,
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="external_kafka",
    )
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": False,
            "output": result.stdout,
            "error": result.stderr or f"rc={result.rc}",
        }
    return {
        "success": True,
        "output": result.stdout,
        "error": "",
    }


def verify_external_kafka_certs(host):
    """Verify external Kafka TLS certificate files exist.

    Checks for ca.crt, user.crt, user.key in the external_kafka
    output directory on the OIM (dynamically resolved from env vars).

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, found, missing, cert_dir.
    """
    cert_dir = _get_cert_dir(host)
    found = []
    missing = []

    for cert_file in OME_KAFKA_CERT_FILES:
        path = f"{cert_dir}/{cert_file}"
        cmd = CMDS["file_exists"].format(path=path)
        result = run_on_host(host, cmd)
        if result.rc == 0 and "exists" in result.stdout:
            found.append(cert_file)
        else:
            missing.append(cert_file)

    return {
        "success": len(missing) == 0,
        "found": found,
        "missing": missing,
        "cert_dir": cert_dir,
    }


def convert_certs_to_pfx(host, pfx_password=""):
    """Convert user.crt + user.key to user.pfx for OME mTLS.

    Runs openssl pkcs12 -export to create the PFX file.

    Args:
        host: Testinfra host connection to the OIM.
        pfx_password: Password for the PFX file (empty = no password).

    Returns:
        dict with keys: success, pfx_path, error.
    """
    cert_dir = _get_cert_dir(host)
    pfx_path = f"{cert_dir}/user.pfx"
    cmd = CMDS["openssl_create_pfx"].format(
        cert_dir=cert_dir,
        password=pfx_password,
    )
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": False,
            "pfx_path": pfx_path,
            "error": result.stderr or f"rc={result.rc}",
        }

    # Verify PFX file was created
    verify_cmd = CMDS["file_exists"].format(path=pfx_path)
    verify_result = run_on_host(host, verify_cmd)
    exists = (
        verify_result.rc == 0
        and "exists" in verify_result.stdout
    )

    return {
        "success": exists,
        "pfx_path": pfx_path,
        "error": "" if exists else "PFX file not created",
    }


def verify_ome_kafka_user_cr(host):
    """Verify the OME KafkaUser CR exists in the telemetry namespace.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, name, error.
    """
    cmd = CMDS["kubectl_get_kafkauser"].format(
        name=OME_KAFKA_USER, namespace=TELEMETRY_NAMESPACE,
    )
    result = run_on_kube_vip(host, cmd)
    exists = result.rc == 0 and "exists" in result.stdout
    return {
        "success": exists,
        "name": OME_KAFKA_USER,
        "error": "" if exists else "KafkaUser not found",
    }


def upload_ome_certs(host, ome_ip, ome_user, ome_password):
    """Upload TLS certificates to OME via REST API.

    Uploads ca.crt (server certificate) via the OME
    ApplicationService.UploadCertificate endpoint.

    Uses OME REST API:
        POST /api/ApplicationService/Actions/
            ApplicationService.UploadCertificate
        Content-Type: application/octet-stream

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address.
        ome_user: OME admin username.
        ome_password: OME admin password.

    Returns:
        dict with keys: success, ca_uploaded, error.
    """
    cert_dir = _get_cert_dir(host)

    # Upload CA cert via OME REST API
    ca_cmd = CMDS["ome_upload_cert"].format(
        ome_ip=ome_ip, user=ome_user, password=ome_password,
        cert_path=f"{cert_dir}/ca.crt",
    )
    ca_result = run_on_host(host, ca_cmd)
    ca_ok = ca_result.rc == 0

    error = ""
    if not ca_ok:
        error = ca_result.stderr or f"rc={ca_result.rc}"
        # Check for API error in JSON response
        try:
            resp = json.loads(ca_result.stdout)
            if "error" in resp:
                error = resp["error"].get("message", error)
        except (json.JSONDecodeError, AttributeError):
            pass

    return {
        "success": ca_ok,
        "ca_uploaded": ca_ok,
        "error": error,
    }
