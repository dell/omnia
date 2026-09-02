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
  - OME Kafka topic and data verification

All shell commands are referenced from ``OME_CMD_TEMPLATES`` in ``ome_vars.py``.
"""

import json
import math
import time

from omnia_auto import read_remote_yaml, run_on_host

from ..vars.common_vars import (
    KAFKA_EXTERNAL_BOOTSTRAP_SVC,
    PLAYBOOK_ENTRY_POINT,
    PLAYBOOK_WORKDIR,
    TELEMETRY_NAMESPACE,
)
from ..vars.ome_vars import (
    KAFKA_BRIDGE_DEFAULT_PORT,
    KAFKA_BRIDGE_SERVICE,
    OME_CMD_TEMPLATES,
    OME_FORWARDER_ID,
    OME_KAFKA_CERT_FILES,
    OME_KAFKA_CERT_SUBDIR,
    OME_KAFKA_CONNECTION_POLL_INTERVAL_SECONDS,
    OME_KAFKA_CONNECTION_TIMEOUT_SECONDS,
    OME_KAFKA_DATA_POLL_INTERVAL_SECONDS,
    OME_KAFKA_DATA_TIMEOUT_SECONDS,
    OME_KAFKA_DETAILS_FILE,
    OME_KAFKA_TOPIC_POLL_INTERVAL_SECONDS,
    OME_KAFKA_TOPIC_TIMEOUT_SECONDS,
    OME_KAFKA_TOPICS,
    OME_KAFKA_USER,
    OME_LOG_TOPIC_SUFFIXES,
    OME_METRIC_TOPIC_SUFFIXES,
)
from .telemetry_func import (
    get_kafka_external_bootstrap,
    get_output_path,
    load_telemetry_config_from_target,
    run_on_kube_vip,
)


def get_ome_pipeline_context(host):
    """Return the deployed OME source and bridge channel configuration.

    The source flags describe which topic families OME is expected to
    publish.  The bridge flags describe which families Vector routes to the
    Victoria backends.  Topic names use the ``ome_identifier`` from the
    deployed telemetry configuration rather than assuming the default
    ``ome`` prefix.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict: Channel flags, resolved topic lists, and configuration state.
    """
    config = load_telemetry_config_from_target(host)
    sources = config.get("telemetry_sources") if isinstance(config, dict) else None
    bridges = config.get("telemetry_bridges") if isinstance(config, dict) else None
    source = sources.get("ome") if isinstance(sources, dict) else None
    bridge = bridges.get("vector_ome") if isinstance(bridges, dict) else None

    source = source if isinstance(source, dict) else {}
    bridge = bridge if isinstance(bridge, dict) else {}
    source_metrics = source.get("metrics_enabled") is True
    source_logs = source.get("logs_enabled") is True
    bridge_metrics = bridge.get("metrics_enabled") is True
    bridge_logs = bridge.get("logs_enabled") is True
    identifier = str(bridge.get("ome_identifier", "ome")).strip() or "ome"

    enabled_suffixes = set()
    if source_metrics:
        enabled_suffixes.update(OME_METRIC_TOPIC_SUFFIXES)
    if source_logs:
        enabled_suffixes.update(OME_LOG_TOPIC_SUFFIXES)

    # Preserve the established display order while applying the configured
    # identifier and filtering out disabled topic families.
    expected_topics = []
    for default_topic in OME_KAFKA_TOPICS:
        suffix = default_topic.rsplit(".", maxsplit=1)[-1]
        if suffix in enabled_suffixes:
            expected_topics.append(f"{identifier}.{suffix}")

    return {
        "config_valid": bool(source) and bool(bridge),
        "identifier": identifier,
        "source_metrics_enabled": source_metrics,
        "source_logs_enabled": source_logs,
        "source_enabled": source_metrics or source_logs,
        "bridge_metrics_enabled": bridge_metrics,
        "bridge_logs_enabled": bridge_logs,
        "bridge_enabled": bridge_metrics or bridge_logs,
        "metrics_pipeline_enabled": source_metrics and bridge_metrics,
        "logs_pipeline_enabled": source_logs and bridge_logs,
        "expected_topics": expected_topics,
    }


def _get_cert_dir(host):
    """Resolve the external_kafka cert directory on the OIM.

    Returns:
        str: e.g. /opt/omnia/telemetry/output/project_default/external_kafka
    """
    return f"{get_output_path(host)}/{OME_KAFKA_CERT_SUBDIR}"


def _is_ome_auth_error(error):
    """Return whether an OME API error represents authentication failure."""
    if not isinstance(error, dict):
        return False
    error_text = " ".join([
        str(error.get("code", "")),
        str(error.get("message", "")),
    ]).lower()
    return any(marker in error_text for marker in (
        "auth", "credential", "unauthorized", "access denied", "forbidden",
        "insufficient privilege", "401", "403",
    ))


def _is_success_http_code(http_code):
    """Return whether an HTTP status code represents success."""
    return 200 <= http_code < 300


def _is_auth_http_code(http_code):
    """Return whether an HTTP status code is an authentication failure."""
    return http_code in (401, 403)


def _format_ome_action_error(result, body, http_code):
    """Build a useful error from an OME action response."""
    detail = body.strip()
    if detail:
        try:
            response = json.loads(detail)
            api_error = response.get("error", response)
            if isinstance(api_error, dict):
                detail = str(
                    api_error.get("message")
                    or api_error.get("code")
                    or detail
                )
        except (json.JSONDecodeError, AttributeError):
            pass
    detail = detail or result.stderr.strip()
    status = f"HTTP {http_code}" if http_code else f"curl rc={result.rc}"
    return f"{status}: {detail}" if detail else status


def verify_ome_kafka_connectivity(host, ome_ip, ome_user,
                                  ome_secret, forwarder_id=10):
    """Check OME Kafka forwarder connectivity status via REST API.

    Uses: GET /api/DataForwardingService/Forwarders({id})/ConnectivityStatus

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address (from test_config.yml).
        ome_user: OME admin username (from test_creds.yml).
        ome_secret: OME admin password (from test_creds.yml).
        forwarder_id: Forwarder ID (default: 10 for Kafka).

    Returns:
        dict with keys: success, status, time_last_connected,
        forwarder_name, forwarder_enabled, error.
    """
    # First get forwarder details
    forwarder_cmd = OME_CMD_TEMPLATES["ome_get_forwarder"].format(
        user=ome_user, secret=ome_secret,
        ome_ip=ome_ip, forwarder_id=forwarder_id,
    )
    result = run_on_host(host, forwarder_cmd)
    forwarder_body, forwarder_http_code = _parse_http_code(result.stdout)
    forwarder_name = ""
    forwarder_enabled = False

    if _is_auth_http_code(forwarder_http_code):
        return {
            "success": False,
            "status": "AuthError",
            "error": f"OME API authentication failed (HTTP {forwarder_http_code})",
        }
    if forwarder_http_code and not _is_success_http_code(forwarder_http_code):
        return {
            "success": False,
            "status": "ApiError",
            "error": f"OME API returned HTTP {forwarder_http_code}",
        }

    if result.rc == 0 and forwarder_body:
        try:
            fwd = json.loads(forwarder_body)
            if "error" in fwd:
                api_error = fwd["error"]
                error_msg = api_error.get(
                    "message", "Unknown error"
                )
                return {
                    "success": False,
                    "status": (
                        "AuthError" if _is_ome_auth_error(api_error)
                        else "ApiError"
                    ),
                    "error": f"API error: {error_msg}",
                }
            forwarder_name = fwd.get("Name", "")
            forwarder_enabled = fwd.get("Enabled", False)
        except json.JSONDecodeError:
            pass

    # Get connectivity status
    status_cmd = OME_CMD_TEMPLATES["ome_get_forwarder_status"].format(
        user=ome_user, secret=ome_secret,
        ome_ip=ome_ip, forwarder_id=forwarder_id,
    )
    result = run_on_host(host, status_cmd)
    status_body, status_http_code = _parse_http_code(result.stdout)

    if _is_auth_http_code(status_http_code):
        return {
            "success": False,
            "status": "AuthError",
            "forwarder_name": forwarder_name,
            "forwarder_enabled": forwarder_enabled,
            "error": f"OME API authentication failed (HTTP {status_http_code})",
        }
    if status_http_code and not _is_success_http_code(status_http_code):
        return {
            "success": False,
            "status": "ApiError",
            "forwarder_name": forwarder_name,
            "forwarder_enabled": forwarder_enabled,
            "error": f"OME API returned HTTP {status_http_code}",
        }

    if result.rc != 0 or not status_body:
        return {
            "success": False,
            "status": "Unreachable",
            "forwarder_name": forwarder_name,
            "forwarder_enabled": forwarder_enabled,
            "error": f"Cannot reach OME at {ome_ip}",
        }

    try:
        data = json.loads(status_body)
        if "error" in data:
            api_error = data["error"]
            error_msg = api_error.get(
                "message", "Authentication failed"
            )
            return {
                "success": False,
                "status": (
                    "AuthError" if _is_ome_auth_error(api_error)
                    else "ApiError"
                ),
                "forwarder_name": forwarder_name,
                "forwarder_enabled": forwarder_enabled,
                "error": error_msg,
            }

        # API returns {"value": [{"Status": "...", ...}]}
        status_list = data.get("value", [])
        if status_list:
            status_obj = status_list[0]
            status = status_obj.get("Status", "Unknown")
            time_connected = status_obj.get("TimeLastConnected", "")
        else:
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


def get_ome_kafka_forwarder_config(host, ome_ip, ome_user, ome_secret,
                                   forwarder_id=OME_FORWARDER_ID):
    """Read the current OME Kafka forwarder configuration.

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address.
        ome_user: OME admin username.
        ome_secret: OME admin password.
        forwarder_id: OME Kafka forwarder ID.

    Returns:
        dict containing the configuration map, current broker, and error.
    """
    cmd = OME_CMD_TEMPLATES["ome_get_forwarder_config"].format(
        ome_ip=ome_ip,
        user=ome_user,
        secret=ome_secret,
        forwarder_id=forwarder_id,
    )
    result = run_on_host(host, cmd)
    body, http_code = _parse_http_code(result.stdout)

    if _is_auth_http_code(http_code):
        return {
            "success": False,
            "status": "AuthError",
            "configurations": {},
            "broker_list": "",
            "error": f"OME API authentication failed (HTTP {http_code})",
        }
    if http_code and not _is_success_http_code(http_code):
        return {
            "success": False,
            "status": "ApiError",
            "configurations": {},
            "broker_list": "",
            "error": f"OME API returned HTTP {http_code}",
        }
    if result.rc != 0 or not body:
        return {
            "success": False,
            "status": "Unreachable",
            "configurations": {},
            "broker_list": "",
            "error": f"Cannot read OME Kafka configuration at {ome_ip}",
        }

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {
            "success": False,
            "status": "ParseError",
            "configurations": {},
            "broker_list": "",
            "error": "Invalid JSON from OME forwarder configuration API",
        }

    if "error" in data:
        api_error = data["error"]
        return {
            "success": False,
            "status": (
                "AuthError" if _is_ome_auth_error(api_error) else "ApiError"
            ),
            "configurations": {},
            "broker_list": "",
            "error": api_error.get("message", "OME API error"),
        }

    items = data.get("value", [])
    if not isinstance(items, list):
        return {
            "success": False,
            "status": "ParseError",
            "configurations": {},
            "broker_list": "",
            "error": "OME forwarder configuration response is not a list",
        }

    configurations = {
        item.get("ConfigurationName"): str(item.get("ConfigurationValue", ""))
        for item in items
        if isinstance(item, dict) and item.get("ConfigurationName")
    }
    return {
        "success": True,
        "status": "Available",
        "configurations": configurations,
        "broker_list": configurations.get("BrokerList", "").strip(),
        "error": "",
    }


def configure_ome_kafka_and_wait(
        host, ome_ip, ome_user, ome_secret, broker_list,
        ome_identifier="ome", forwarder_id=OME_FORWARDER_ID,
        timeout_seconds=OME_KAFKA_CONNECTION_TIMEOUT_SECONDS,
        poll_interval_seconds=OME_KAFKA_CONNECTION_POLL_INTERVAL_SECONDS,
        status_callback=None, force_configuration=False):
    """Configure OME Kafka and wait for asynchronous reconnection.

    A certificate upload can temporarily reject TestConnection or Save while
    OME reloads its trust material. Those actions are retried within one
    five-minute polling window, and ConnectivityStatus remains authoritative.

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address.
        ome_user: OME admin username.
        ome_secret: OME admin password.
        broker_list: Native Kafka mTLS bootstrap endpoint.
        ome_identifier: OME identifier sent in forwarder settings.
        forwarder_id: OME Kafka forwarder ID.
        timeout_seconds: Connectivity polling window.
        poll_interval_seconds: Delay between retry cycles.
        status_callback: Optional callable receiving attempt, max_attempts,
            and the latest status result.
        force_configuration: Run TestConnection and Save even when the
            forwarder is currently connected, used to reconcile a stale broker.

    Returns:
        Latest connectivity result plus action results and timing details.
    """
    timeout_seconds = max(0, timeout_seconds)
    poll_interval_seconds = max(0.1, poll_interval_seconds)
    max_attempts = math.ceil(timeout_seconds / poll_interval_seconds) + 1
    started_at = time.monotonic()
    attempts = 0
    test_attempts = 0
    save_attempts = 0
    test_accepted = False
    settings_saved = False
    connection_confirmed = False
    must_save_settings = force_configuration
    test_result = None
    settings_result = None
    result = {
        "success": False,
        "status": "Unknown",
        "error": "OME Kafka connectivity was not checked",
    }

    while True:
        attempts += 1
        result = verify_ome_kafka_connectivity(
            host, ome_ip, ome_user, ome_secret, forwarder_id,
        )
        if status_callback:
            status_callback(attempts, max_attempts, result)

        if result["success"] and (not must_save_settings or settings_saved):
            connection_confirmed = True
            break
        if result.get("status") == "AuthError":
            break
        if time.monotonic() - started_at >= timeout_seconds:
            break

        if not test_accepted:
            test_attempts += 1
            test_result = send_ome_kafka_test_connection(
                host, ome_ip, ome_user, ome_secret,
                broker_list, ome_identifier, forwarder_id,
            )
            test_accepted = test_result["success"]
            if _is_auth_http_code(test_result.get("http_code", 0)):
                result = {
                    "success": False,
                    "status": "AuthError",
                    "error": test_result["error"],
                }
                break

        if test_accepted and not settings_saved:
            save_attempts += 1
            settings_result = update_ome_forwarder_settings(
                host, ome_ip, ome_user, ome_secret,
                broker_list, ome_identifier, forwarder_id,
            )
            settings_saved = settings_result["success"]
            if _is_auth_http_code(settings_result.get("http_code", 0)):
                result = {
                    "success": False,
                    "status": "AuthError",
                    "error": settings_result["error"],
                }
                break

        remaining_seconds = timeout_seconds - (
            time.monotonic() - started_at
        )
        if remaining_seconds <= 0:
            break
        time.sleep(min(poll_interval_seconds, remaining_seconds))

    elapsed_seconds = time.monotonic() - started_at
    final_result = dict(result)
    if not connection_confirmed:
        final_result["success"] = False
        if result.get("success") and must_save_settings:
            final_result["status"] = "Reconnecting"
            final_result["error"] = (
                "OME Kafka connection was not confirmed after updating settings"
            )
    final_result.update({
        "attempts": attempts,
        "test_connection_attempts": test_attempts,
        "settings_update_attempts": save_attempts,
        "test_connection": test_result,
        "settings_update": settings_result,
        "elapsed_seconds": round(elapsed_seconds, 1),
        "timed_out": (
            not final_result["success"]
            and final_result.get("status") != "AuthError"
            and elapsed_seconds >= timeout_seconds
        ),
    })
    return final_result


def get_ome_forwarders(host, ome_ip, ome_user, ome_secret):
    """List all OME DataForwardingService forwarders.

    Uses: GET /api/DataForwardingService/Forwarders

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address (from test_config.yml).
        ome_user: OME admin username (from test_creds.yml).
        ome_secret: OME admin password (from test_creds.yml).

    Returns:
        dict with keys: success, forwarders (list), error.
    """
    cmd = OME_CMD_TEMPLATES["ome_get_forwarders_list"].format(
        user=ome_user, secret=ome_secret, ome_ip=ome_ip,
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

def run_external_kafka_playbook():
    """Run the external_kafka_connect playbook to extract TLS certs.

    Runs: ansible-playbook telemetry.yml --tags external_kafka

    Uses omnia_auto.run_playbook which handles local/remote execution
    based on test_config.yml settings.

    Returns:
        dict with keys: success, output, error, duration.
    """
    from omnia_auto import run_playbook
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="external_kafka",
        playbook_workdir=PLAYBOOK_WORKDIR,
    )
    return {
        "success": result.get("success", False),
        "output": result.get("output", ""),
        "error": result.get("error", ""),
        "duration": result.get("duration", 0),
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
        cmd = OME_CMD_TEMPLATES["file_exists"].format(path=path)
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


def verify_external_kafka_connection_details(host):
    """Verify the exported native Kafka and HTTP Bridge endpoints.

    The native mTLS bootstrap is the endpoint configured in OME. The HTTP
    Bridge is a separate REST endpoint used only by validation consumers.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict containing the exported and live endpoints plus any mismatches.
    """
    details_path = f"{_get_cert_dir(host)}/{OME_KAFKA_DETAILS_FILE}"
    details = read_remote_yaml(host, details_path)
    kafka_details = details.get("kafka", {}) if isinstance(details, dict) else {}
    if not isinstance(kafka_details, dict):
        kafka_details = {}

    bridge_details = kafka_details.get("bridge", {})
    if not isinstance(bridge_details, dict):
        bridge_details = {}

    exported_bootstrap = str(kafka_details.get("bootstrap_server", ""))
    exported_bootstrap_service = str(
        kafka_details.get("loadbalancer_service", "")
    )
    exported_bridge = str(bridge_details.get("endpoint", ""))
    exported_bridge_service = str(
        bridge_details.get("loadbalancer_service", "")
    )

    expected_bootstrap = get_kafka_external_bootstrap(host)
    bridge_ip = get_kafka_bridge_ip(host)
    bridge_port = get_kafka_bridge_port(host) if bridge_ip else ""
    expected_bridge = (
        f"http://{bridge_ip}:{bridge_port}" if bridge_ip and bridge_port else ""
    )

    mismatches = []
    if not details:
        mismatches.append(f"Connection details file is missing: {details_path}")
    if not expected_bootstrap:
        mismatches.append("Native Kafka bootstrap service is unavailable")
    elif exported_bootstrap != expected_bootstrap:
        mismatches.append(
            f"bootstrap_server is '{exported_bootstrap}', expected "
            f"'{expected_bootstrap}'"
        )
    if exported_bootstrap_service != KAFKA_EXTERNAL_BOOTSTRAP_SVC:
        mismatches.append(
            f"loadbalancer_service is '{exported_bootstrap_service}', expected "
            f"'{KAFKA_EXTERNAL_BOOTSTRAP_SVC}'"
        )
    if not expected_bridge:
        mismatches.append("Kafka HTTP Bridge service is unavailable")
    elif exported_bridge != expected_bridge:
        mismatches.append(
            f"bridge.endpoint is '{exported_bridge}', expected "
            f"'{expected_bridge}'"
        )
    if exported_bridge_service != KAFKA_BRIDGE_SERVICE:
        mismatches.append(
            f"bridge.loadbalancer_service is '{exported_bridge_service}', "
            f"expected '{KAFKA_BRIDGE_SERVICE}'"
        )

    return {
        "success": len(mismatches) == 0,
        "details_path": details_path,
        "bootstrap_server": exported_bootstrap,
        "expected_bootstrap": expected_bootstrap,
        "bridge_endpoint": exported_bridge,
        "expected_bridge": expected_bridge,
        "mismatches": mismatches,
        "error": "; ".join(mismatches),
    }


def convert_certs_to_pfx(host, pfx_secret=""):
    """Convert user.crt + user.key to user.pfx for OME mTLS.

    Runs openssl pkcs12 -export to create the PFX file.

    Args:
        host: Testinfra host connection to the OIM.
        pfx_secret: Password for the PFX file (empty = no password).

    Returns:
        dict with keys: success, pfx_path, error.
    """
    cert_dir = _get_cert_dir(host)
    pfx_path = f"{cert_dir}/user.pfx"
    cmd = OME_CMD_TEMPLATES["openssl_create_pfx"].format(
        cert_dir=cert_dir,
        secret=pfx_secret,
    )
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": False,
            "pfx_path": pfx_path,
            "error": result.stderr or f"rc={result.rc}",
        }

    # Verify PFX file was created
    verify_cmd = OME_CMD_TEMPLATES["file_exists"].format(path=pfx_path)
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
    cmd = OME_CMD_TEMPLATES["kafka_user_exists"].format(
        user=OME_KAFKA_USER, namespace=TELEMETRY_NAMESPACE,
    )
    result = run_on_kube_vip(host, cmd)
    # Command returns KafkaUser name if exists, empty if not
    exists = result.rc == 0 and OME_KAFKA_USER in result.stdout
    return {
        "success": exists,
        "name": OME_KAFKA_USER,
        "error": "" if exists else "KafkaUser not found",
    }


def _read_file_base64(host, file_path):
    """Read a file and return its base64-encoded content.

    Args:
        host: Testinfra host connection.
        file_path: Path to the file to read.

    Returns:
        str: Base64-encoded content, or empty string on error.
    """
    cmd = f"base64 -w0 {file_path} 2>/dev/null"
    result = run_on_host(host, cmd)
    if result.rc == 0:
        return result.stdout.strip()
    return ""


def _parse_http_code(output):
    """Extract HTTP code from curl output with -w 'HTTP_CODE:%{http_code}'.

    Args:
        output: Raw curl output string.

    Returns:
        tuple: (body, http_code) where http_code is int or 0 on error.
    """
    if "HTTP_CODE:" in output:
        parts = output.rsplit("HTTP_CODE:", 1)
        body = parts[0].strip()
        try:
            http_code = int(parts[1].strip())
        except ValueError:
            http_code = 0
        return body, http_code
    return output, 0


def upload_ome_server_cert(host, ome_ip, ome_user, ome_secret):
    """Upload CA certificate (server cert) to OME via REST API.

    Uses OME REST API:
        POST /api/ApplicationService/Actions/
            ApplicationService.UploadServerCertificate
        Content-Type: application/json
        Body: {"CertData": "<base64>", "CertFormat": "X_509",
               "ClientType": "KAFKA"}

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address.
        ome_user: OME admin username.
        ome_secret: OME admin password.

    Returns:
        dict with keys: success, http_code, error.
    """
    cert_dir = _get_cert_dir(host)
    ca_crt_path = f"{cert_dir}/ca.crt"

    # Read CA cert content and encode as base64 for the JSON payload
    ca_b64 = _read_file_base64(host, ca_crt_path)
    if not ca_b64:
        return {
            "success": False,
            "http_code": 0,
            "error": f"Cannot read {ca_crt_path}",
        }

    cmd = OME_CMD_TEMPLATES["ome_upload_server_cert"].format(
        ome_ip=ome_ip, user=ome_user, secret=ome_secret,
        cert_data_b64=ca_b64,
    )
    result = run_on_host(host, cmd)
    _, http_code = _parse_http_code(result.stdout)

    # 204 No Content = success
    success = http_code == 204
    error = "" if success else f"HTTP {http_code}"

    return {
        "success": success,
        "http_code": http_code,
        "error": error,
    }


def upload_ome_client_cert(host, ome_ip, ome_user, ome_secret,
                           pfx_secret=""):
    """Upload client certificate (PFX) to OME via REST API.

    Uses OME REST API:
        POST /api/ApplicationService/Actions/
            ApplicationService.UploadClientCertificate
        Content-Type: application/json
        Body: {"CertData": "<base64>", "CertFormat": "PKCS_12",
               "ClientType": "KAFKA", "Passphrase": "<password>"}

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address.
        ome_user: OME admin username.
        ome_secret: OME admin password.
        pfx_secret: Password for the PFX file.

    Returns:
        dict with keys: success, http_code, error.
    """
    cert_dir = _get_cert_dir(host)
    pfx_path = f"{cert_dir}/user.pfx"

    # Read PFX content and encode as base64 for the JSON payload
    pfx_b64 = _read_file_base64(host, pfx_path)
    if not pfx_b64:
        return {
            "success": False,
            "http_code": 0,
            "error": f"Cannot read {pfx_path}",
        }

    cmd = OME_CMD_TEMPLATES["ome_upload_client_cert"].format(
        ome_ip=ome_ip, user=ome_user, secret=ome_secret,
        cert_data_b64=pfx_b64, pfx_secret=pfx_secret,
    )
    result = run_on_host(host, cmd)
    _, http_code = _parse_http_code(result.stdout)

    # 204 No Content = success
    success = http_code == 204
    error = "" if success else f"HTTP {http_code}"

    return {
        "success": success,
        "http_code": http_code,
        "error": error,
    }


def view_ome_client_cert(host, ome_ip, ome_user, ome_secret):
    """View the uploaded client certificate details from OME.

    Uses OME REST API:
        POST /api/ApplicationService/Actions/
            ApplicationService.ViewClientCertificate
        Body: {"ClientType": "KAFKA"}

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address.
        ome_user: OME admin username.
        ome_secret: OME admin password.

    Returns:
        dict with keys: success, cert_info, error.
    """
    cmd = OME_CMD_TEMPLATES["ome_view_client_cert"].format(
        ome_ip=ome_ip, user=ome_user, secret=ome_secret,
    )
    result = run_on_host(host, cmd)

    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "cert_info": None,
            "error": "Cannot reach OME",
        }

    try:
        data = json.loads(result.stdout)
        if isinstance(data, list) and len(data) > 0:
            cert_info = data[0]
            issued_to = cert_info.get("IssuedTo") or {}
            issued_by = cert_info.get("IssuedBy") or {}
            return {
                "success": True,
                "cert_info": cert_info,
                "issued_to": issued_to.get("DistinguishedName", ""),
                "issued_by": issued_by.get("DistinguishedName", ""),
                "issued_by_org": issued_by.get("BusinessName", ""),
                "valid_from": cert_info.get("ValidFrom", ""),
                "valid_to": cert_info.get("ValidTo", ""),
                "error": "",
            }
        return {
            "success": False,
            "cert_info": None,
            "error": "No certificate found",
        }
    except json.JSONDecodeError:
        return {
            "success": False,
            "cert_info": None,
            "error": "Invalid JSON response",
        }


def get_local_cert_details(host):
    """Read subject/issuer/validity of the locally generated user.crt.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, subject_cn, issuer_cn, issuer_org,
        not_before, not_after, serial, error.
    """
    cert_path = f"{_get_cert_dir(host)}/user.crt"
    cmd = OME_CMD_TEMPLATES["openssl_cert_details"].format(cert_path=cert_path)
    result = run_on_host(host, cmd)

    if result.rc != 0:
        return {
            "success": False,
            "error": f"Cannot read {cert_path}: {result.stderr}",
        }

    details = {"success": True, "error": ""}
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("subject="):
            details["subject_cn"] = _extract_dn_field(line, "CN")
        elif line.startswith("issuer="):
            details["issuer_cn"] = _extract_dn_field(line, "CN")
            details["issuer_org"] = _extract_dn_field(line, "O")
        elif line.startswith("notBefore="):
            details["not_before"] = line.split("=", 1)[1].strip()
        elif line.startswith("notAfter="):
            details["not_after"] = line.split("=", 1)[1].strip()
        elif line.startswith("serial="):
            details["serial"] = line.split("=", 1)[1].strip()

    return details


def _extract_dn_field(dn_line, field):
    """Extract a field (e.g. CN, O) from an openssl DN line.

    Args:
        dn_line: Line such as ``issuer=O=io.strimzi, CN=clients-ca v0``.
        field: DN field name to extract (``CN``, ``O``, ...).

    Returns:
        str: Field value, or empty string when not present.
    """
    dn = dn_line.split("=", 1)[1] if "=" in dn_line else dn_line
    for part in dn.split(","):
        part = part.strip()
        if part.startswith(f"{field}="):
            return part.split("=", 1)[1].strip()
    return ""


def compare_ome_cert_with_local(host, ome_ip, ome_user, ome_secret):
    """Compare the certificate uploaded to OME with the local user.crt.

    Confirms OME is using the exact certificate generated by the
    external_kafka playbook by matching subject, issuer and validity.

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address.
        ome_user: OME admin username.
        ome_secret: OME admin credential.

    Returns:
        dict with keys: success, matches, mismatches, ome_cert, local_cert.
    """
    ome_cert = view_ome_client_cert(host, ome_ip, ome_user, ome_secret)
    if not ome_cert["success"]:
        return {
            "success": False,
            "error": ome_cert.get("error", "Cannot read OME certificate"),
            "matches": [],
            "mismatches": [],
        }

    local_cert = get_local_cert_details(host)
    if not local_cert["success"]:
        return {
            "success": False,
            "error": local_cert.get("error", "Cannot read local certificate"),
            "matches": [],
            "mismatches": [],
            "ome_cert": ome_cert,
        }

    matches = []
    mismatches = []

    # Subject CN must be identical
    _compare_field(
        "Subject CN", local_cert.get("subject_cn", ""),
        ome_cert.get("issued_to", ""), matches, mismatches,
    )
    # Issuer CN must be identical
    _compare_field(
        "Issuer CN", local_cert.get("issuer_cn", ""),
        ome_cert.get("issued_by", ""), matches, mismatches,
    )
    # Issuer organisation must be identical
    _compare_field(
        "Issuer Org", local_cert.get("issuer_org", ""),
        ome_cert.get("issued_by_org", ""), matches, mismatches,
    )
    # Validity window must line up (OME reports ISO-8601, openssl reports
    # "Aug 27 11:42:36 2026 GMT" - compare the normalised timestamps)
    _compare_field(
        "Valid From", _normalize_cert_time(local_cert.get("not_before", "")),
        _normalize_cert_time(ome_cert.get("valid_from", "")),
        matches, mismatches,
    )
    _compare_field(
        "Valid To", _normalize_cert_time(local_cert.get("not_after", "")),
        _normalize_cert_time(ome_cert.get("valid_to", "")),
        matches, mismatches,
    )

    return {
        "success": len(mismatches) == 0,
        "matches": matches,
        "mismatches": mismatches,
        "ome_cert": ome_cert,
        "local_cert": local_cert,
        "error": "" if not mismatches else f"{len(mismatches)} field(s) differ",
    }


def _compare_field(name, local_value, ome_value, matches, mismatches):
    """Record whether a local and OME certificate field agree.

    Args:
        name: Human-readable field name.
        local_value: Value read from the local certificate.
        ome_value: Value reported by OME.
        matches: List collecting matching fields (mutated).
        mismatches: List collecting differing fields (mutated).
    """
    if local_value and local_value == ome_value:
        matches.append({"field": name, "value": local_value})
    else:
        mismatches.append({
            "field": name, "local": local_value, "ome": ome_value,
        })


def _normalize_cert_time(value):
    """Normalise a certificate timestamp to ``YYYY-MM-DDTHH:MM:SS``.

    Accepts both the OME ISO-8601 form (``2026-08-27T11:42:36Z``) and the
    openssl form (``Aug 27 11:42:36 2026 GMT``).

    Args:
        value: Raw timestamp string.

    Returns:
        str: Normalised timestamp, or the original value if unparseable.
    """
    if not value:
        return ""
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%b %d %H:%M:%S %Y %Z"):
        try:
            return time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.strptime(value.strip(), fmt),
            )
        except ValueError:
            continue
    return value.strip()


def send_ome_kafka_test_connection(
    host, ome_ip, ome_user, ome_secret, broker_list,
    ome_identifier="ome", forwarder_id=10,
):
    """Test OME Kafka connection via REST API.

    Uses OME REST API:
        POST /api/DataForwardingService/Actions/
            DataForwardingService.TestConnection

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address.
        ome_user: OME admin username.
        ome_secret: OME admin password.
        broker_list: Kafka bootstrap server (e.g., "192.168.13.161:9094").
        ome_identifier: OME identifier string (default: "ome").
        forwarder_id: Forwarder ID (default: 10 for Kafka).

    Returns:
        dict with keys: success, http_code, error.
    """
    cmd = OME_CMD_TEMPLATES["ome_test_kafka_connection"].format(
        ome_ip=ome_ip, user=ome_user, secret=ome_secret,
        forwarder_id=forwarder_id, ome_identifier=ome_identifier,
        broker_list=broker_list,
    )
    result = run_on_host(host, cmd)
    body, http_code = _parse_http_code(result.stdout)

    # The supported OME TestConnection action documents HTTP 200 as success.
    success = result.rc == 0 and http_code == 200
    error = "" if success else _format_ome_action_error(
        result, body, http_code,
    )

    return {
        "success": success,
        "http_code": http_code,
        "error": error,
    }


def update_ome_forwarder_settings(host, ome_ip, ome_user, ome_secret,
                                  broker_list, ome_identifier="ome",
                                  forwarder_id=10):
    """Update OME Kafka forwarder settings via REST API.

    Uses OME REST API:
        POST /api/DataForwardingService/Actions/
            DataForwardingService.ForwarderSettings

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address.
        ome_user: OME admin username.
        ome_secret: OME admin password.
        broker_list: Kafka bootstrap server (e.g., "192.168.13.161:9094").
        ome_identifier: OME identifier string (default: "ome").
        forwarder_id: Forwarder ID (default: 10 for Kafka).

    Returns:
        dict with keys: success, http_code, error.
    """
    cmd = OME_CMD_TEMPLATES["ome_update_forwarder"].format(
        ome_ip=ome_ip, user=ome_user, secret=ome_secret,
        forwarder_id=forwarder_id, ome_identifier=ome_identifier,
        broker_list=broker_list,
    )
    result = run_on_host(host, cmd)
    body, http_code = _parse_http_code(result.stdout)

    # The supported OME ForwarderSettings action documents HTTP 200 as success.
    success = result.rc == 0 and http_code == 200
    error = "" if success else _format_ome_action_error(
        result, body, http_code,
    )

    return {
        "success": success,
        "http_code": http_code,
        "error": error,
    }


def configure_ome_kafka_full(host, ome_ip, ome_user, ome_secret,
                             broker_list, pfx_secret="",
                             ome_identifier="ome", forwarder_id=10):
    """Full OME Kafka configuration: upload certs, test, and save settings.

    This function performs the complete OME Kafka configuration:
    1. Run external_kafka_connect playbook to extract TLS certs
    2. Convert certs to PFX format
    3. Upload server certificate (CA) to OME
    4. Upload client certificate (PFX) to OME
    5. Test Kafka connection
    6. Save forwarder settings

    Args:
        host: Testinfra host connection to the OIM.
        ome_ip: OME appliance IP address.
        ome_user: OME admin username.
        ome_secret: OME admin password.
        broker_list: Kafka bootstrap server (e.g., "192.168.13.161:9094").
        pfx_secret: Password for the PFX file.
        ome_identifier: OME identifier string (default: "ome").
        forwarder_id: Forwarder ID (default: 10 for Kafka).

    Returns:
        dict with keys: success, steps_completed, error.
    """
    steps = []

    # Step 1: Run external_kafka playbook
    playbook_result = run_external_kafka_playbook()
    if not playbook_result["success"]:
        return {
            "success": False,
            "steps_completed": steps,
            "error": f"Playbook failed: {playbook_result['error']}",
        }
    steps.append("external_kafka_playbook")

    # Step 2: Verify certs exist
    certs_result = verify_external_kafka_certs(host)
    if not certs_result["success"]:
        return {
            "success": False,
            "steps_completed": steps,
            "error": f"Missing certs: {certs_result['missing']}",
        }
    steps.append("verify_certs")

    # Step 3: Convert to PFX
    pfx_result = convert_certs_to_pfx(host, pfx_secret)
    if not pfx_result["success"]:
        return {
            "success": False,
            "steps_completed": steps,
            "error": f"PFX conversion failed: {pfx_result['error']}",
        }
    steps.append("convert_pfx")

    # Step 4: Upload server cert (CA)
    server_result = upload_ome_server_cert(
        host, ome_ip, ome_user, ome_secret,
    )
    if not server_result["success"]:
        return {
            "success": False,
            "steps_completed": steps,
            "error": f"Server cert upload failed: {server_result['error']}",
        }
    steps.append("upload_server_cert")

    # Step 5: Upload client cert (PFX)
    client_result = upload_ome_client_cert(
        host, ome_ip, ome_user, ome_secret, pfx_secret,
    )
    if not client_result["success"]:
        return {
            "success": False,
            "steps_completed": steps,
            "error": f"Client cert upload failed: {client_result['error']}",
        }
    steps.append("upload_client_cert")

    # Step 6: Test connection
    test_result = send_ome_kafka_test_connection(
        host, ome_ip, ome_user, ome_secret,
        broker_list, ome_identifier, forwarder_id,
    )
    if not test_result["success"]:
        return {
            "success": False,
            "steps_completed": steps,
            "error": f"Connection test failed: {test_result['error']}",
        }
    steps.append("test_connection")

    # Step 7: Save forwarder settings
    settings_result = update_ome_forwarder_settings(
        host, ome_ip, ome_user, ome_secret,
        broker_list, ome_identifier, forwarder_id,
    )
    if not settings_result["success"]:
        return {
            "success": False,
            "steps_completed": steps,
            "error": f"Settings update failed: {settings_result['error']}",
        }
    steps.append("update_settings")

    return {
        "success": True,
        "steps_completed": steps,
        "error": "",
    }


# =========================================================================
# OME Kafka Data Verification Functions
# =========================================================================

def get_kafka_bridge_ip(host):
    """Get the Kafka bridge LoadBalancer IP.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        str: Bridge IP or empty string if not found.
    """
    cmd = OME_CMD_TEMPLATES["get_bridge_lb_ip"].format(
        namespace=TELEMETRY_NAMESPACE,
        service=KAFKA_BRIDGE_SERVICE,
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc == 0:
        return result.stdout.strip()
    return ""


def get_kafka_bridge_port(host):
    """Get the Kafka bridge LoadBalancer port from service.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        str: Bridge port or default port if not found.
    """
    cmd = OME_CMD_TEMPLATES["get_bridge_lb_port"].format(
        namespace=TELEMETRY_NAMESPACE,
        service=KAFKA_BRIDGE_SERVICE,
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc == 0 and result.stdout.strip():
        return result.stdout.strip()
    return KAFKA_BRIDGE_DEFAULT_PORT


def verify_ome_kafka_topics(
        host, timeout_seconds=OME_KAFKA_TOPIC_TIMEOUT_SECONDS,
        poll_interval_seconds=OME_KAFKA_TOPIC_POLL_INTERVAL_SECONDS,
        expected_topics=None):
    """Verify OME Kafka topics exist via REST proxy.

    Polls until the requested OME topics are present or the timeout expires.
    OME creates topics asynchronously after the forwarder reconnects.  When
    no explicit list is supplied, all canonical OME topics are checked for
    backward compatibility.

    Args:
        host: Testinfra host connection to the OIM.
        timeout_seconds: Maximum time to wait for all topics.
        poll_interval_seconds: Delay between topic-list requests.
        expected_topics: Topic names required by the enabled source channels.

    Returns:
        dict with topic results, endpoint, attempts, elapsed time, and error.
    """
    required_topics = list(
        OME_KAFKA_TOPICS if expected_topics is None else expected_topics
    )
    if not required_topics:
        return {
            "success": True,
            "found_topics": [],
            "missing_topics": [],
            "all_topics": [],
            "expected_topics": [],
            "bridge_ip": "",
            "port": "",
            "attempts": 0,
            "elapsed_seconds": 0.0,
            "error": "",
        }

    bridge_ip = get_kafka_bridge_ip(host)
    if not bridge_ip:
        return {
            "success": False,
            "error": "Kafka bridge IP not found",
            "found_topics": [],
            "missing_topics": required_topics,
            "expected_topics": required_topics,
        }

    port = get_kafka_bridge_port(host)
    cmd = OME_CMD_TEMPLATES["rest_list_topics"].format(
        bridge_ip=bridge_ip,
        port=port,
    )
    timeout_seconds = max(0, timeout_seconds)
    poll_interval_seconds = max(0.1, poll_interval_seconds)
    started_at = time.monotonic()
    attempts = 0
    all_topics = []
    found_topics = []
    missing_topics = list(required_topics)
    last_error = ""

    while True:
        attempts += 1
        result = run_on_kube_vip(host, cmd)
        if result.rc != 0:
            last_error = (
                f"Failed to get topics: {result.stderr.strip() or 'curl failed'}"
            )
        else:
            try:
                parsed_topics = json.loads(result.stdout)
                if isinstance(parsed_topics, list):
                    last_error = ""
                    all_topics = parsed_topics
                    found_topics = [
                        topic for topic in required_topics
                        if topic in all_topics
                    ]
                    missing_topics = [
                        topic for topic in required_topics
                        if topic not in all_topics
                    ]
                    if not missing_topics:
                        break
                else:
                    last_error = "Kafka Bridge returned a non-list topic response"
            except json.JSONDecodeError:
                last_error = "Failed to parse topics JSON"

        elapsed_seconds = time.monotonic() - started_at
        remaining_seconds = timeout_seconds - elapsed_seconds
        if remaining_seconds <= 0:
            break
        time.sleep(min(poll_interval_seconds, remaining_seconds))

    return {
        "success": len(missing_topics) == 0,
        "found_topics": found_topics,
        "missing_topics": missing_topics,
        "all_topics": all_topics,
        "expected_topics": required_topics,
        "bridge_ip": bridge_ip,
        "port": port,
        "attempts": attempts,
        "elapsed_seconds": round(time.monotonic() - started_at, 1),
        "error": last_error,
    }


def verify_ome_data_in_kafka(
        host, topic="ome.telemetry",
        timeout_seconds=OME_KAFKA_DATA_TIMEOUT_SECONDS,
        poll_interval_seconds=OME_KAFKA_DATA_POLL_INTERVAL_SECONDS):
    """Verify OME data is flowing to Kafka topic.

    Uses Kafka REST proxy to create a consumer, subscribe to topic,
    and consume records to verify data presence.

    Args:
        host: Testinfra host connection to the OIM.
        topic: Kafka topic to consume from (default: ome.telemetry).
        timeout_seconds: Timeout for consuming records (default 120s).
        poll_interval_seconds: Delay between consume requests (default 2s).

    Returns:
        dict with keys: success, records_found, sample_records, error.
    """
    bridge_ip = get_kafka_bridge_ip(host)
    if not bridge_ip:
        return {
            "success": False,
            "error": "Kafka bridge IP not found",
            "records_found": 0,
            "sample_records": [],
        }

    port = get_kafka_bridge_port(host)
    consumer_group = f"ome-verify-{int(time.time()) % 10000}"
    consumer_name = "ome-verify-consumer"
    records_found = []
    sample_records = []
    last_consume_error = ""
    consume_attempts = 0

    try:
        # Step 1: Create consumer with 'earliest' offset to get existing data
        create_cmd = OME_CMD_TEMPLATES["rest_create_consumer"].format(
            bridge_ip=bridge_ip,
            port=port,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
            offset="earliest",
        )
        result = run_on_kube_vip(host, create_cmd)
        if result.rc != 0 or "error_code" in result.stdout:
            error_detail = result.stdout.strip() or result.stderr.strip()
            return {
                "success": False,
                "error": f"Failed to create consumer: {error_detail}",
                "records_found": 0,
                "sample_records": [],
                "bridge_ip": bridge_ip,
            }

        # Step 2: Subscribe to topic
        subscribe_cmd = OME_CMD_TEMPLATES["rest_subscribe_topic"].format(
            bridge_ip=bridge_ip,
            port=port,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
            topic=topic,
        )
        subscribe_result = run_on_kube_vip(host, subscribe_cmd)
        if subscribe_result.rc != 0:
            error_detail = (
                subscribe_result.stdout.strip()
                or subscribe_result.stderr.strip()
            )
            return {
                "success": False,
                "error": f"Failed to subscribe to '{topic}': {error_detail}",
                "records_found": 0,
                "sample_records": [],
                "bridge_ip": bridge_ip,
            }

        # Step 3: Consume records with timeout
        consume_cmd = OME_CMD_TEMPLATES["rest_consume_records"].format(
            bridge_ip=bridge_ip,
            port=port,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
        )

        timeout_seconds = max(0, timeout_seconds)
        poll_interval_seconds = max(0.1, poll_interval_seconds)
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout_seconds:
            consume_attempts += 1
            result = run_on_kube_vip(host, consume_cmd)

            if result.rc != 0:
                last_consume_error = (
                    result.stderr.strip() or f"curl failed with rc={result.rc}"
                )
            elif result.stdout.strip().startswith("["):
                try:
                    records = json.loads(result.stdout)
                    last_consume_error = ""
                    for record in records:
                        records_found.append(record)
                        # Keep up to 3 sample records
                        if len(sample_records) < 3:
                            sample_records.append(record)
                except json.JSONDecodeError:
                    last_consume_error = "Kafka Bridge returned invalid JSON"
            else:
                last_consume_error = (
                    "Kafka Bridge returned an unexpected records response"
                )

            # If we found records, we can stop
            if records_found:
                break

            remaining_seconds = timeout_seconds - (
                time.monotonic() - start_time
            )
            if remaining_seconds <= 0:
                break
            time.sleep(min(poll_interval_seconds, remaining_seconds))

    finally:
        # Step 4: Delete consumer (cleanup)
        delete_cmd = OME_CMD_TEMPLATES["rest_delete_consumer"].format(
            bridge_ip=bridge_ip,
            port=port,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
        )
        run_on_kube_vip(host, delete_cmd)

    summaries = [_summarize_ome_record(r) for r in sample_records]
    total_entries = sum(s["entry_count"] for s in summaries)

    return {
        "success": len(records_found) > 0,
        "records_found": len(records_found),
        "sample_records": sample_records,
        "record_summaries": summaries,
        "total_entries": total_entries,
        "topic": topic,
        "bridge_ip": bridge_ip,
        "port": port,
        "attempts": consume_attempts,
        "elapsed_seconds": round(time.monotonic() - start_time, 1),
        "error": (
            "" if records_found
            else last_consume_error
            or f"No data found in topic '{topic}' within {timeout_seconds}s"
        ),
    }


def _summarize_ome_record(record):
    """Normalise one OME Kafka record into a display-friendly summary.

    OME uses a different payload shape per topic: ``ome.telemetry`` sends a
    bare list of devices, while the remaining topics wrap the list in a
    single ``System`` or ``Data`` key. Both shapes are flattened here so
    callers can render every topic the same way.

    Args:
        record: Raw record returned by the Kafka REST proxy.

    Returns:
        dict with keys: partition, offset, timestamp, payload_key,
        entry_count, entries.
    """
    value = record.get("value")
    payload_key = ""

    if isinstance(value, dict) and len(value) == 1:
        payload_key = next(iter(value))
        value = value[payload_key]

    entries = value if isinstance(value, list) else [value]
    entries = [e for e in entries if isinstance(e, dict)]

    return {
        "partition": record.get("partition"),
        "offset": record.get("offset"),
        "timestamp": record.get("timestamp"),
        "payload_key": payload_key,
        "entry_count": len(entries),
        "entries": [_summarize_ome_entry(e) for e in entries],
    }


def _summarize_ome_entry(entry):
    """Reduce a single OME payload entry to an identifier plus key fields.

    Args:
        entry: One device/alert/log entry from an OME payload.

    Returns:
        dict with keys: identifier, metrics, fields.
    """
    identifier = ""
    for key in ("Identifier", "AlertIdentifier", "AlertId", "Id"):
        if entry.get(key):
            identifier = str(entry[key])
            break

    metrics = [
        {
            "name": m.get("MetricId", ""),
            "component": m.get("ComponentId", ""),
            "value": _first_or_value(m.get("MetricValue")),
            "timestamp": _first_or_value(m.get("TimeStamp")),
        }
        for m in entry.get("Metric", []) or []
        if isinstance(m, dict)
    ]

    # Non-metric scalar fields give useful context for alerts/logs/health
    skip = {"Metric", "Component", "MessageArguments"}
    fields = {
        k: v for k, v in entry.items()
        if k not in skip and not isinstance(v, (list, dict))
    }

    return {"identifier": identifier, "metrics": metrics, "fields": fields}


def _first_or_value(value):
    """Return the first element of a list, or the value itself.

    OME reports ``MetricValue``/``TimeStamp`` as parallel lists of samples;
    the newest single sample is enough for reporting.

    Args:
        value: A list of samples or a scalar.

    Returns:
        The first sample, or the original scalar.
    """
    if isinstance(value, list):
        return value[0] if value else ""
    return value if value is not None else ""
