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
VAST — Module-Specific Verification Functions.

Handles:
  - VAST external headless service verification
  - VAST VMServiceScrape CR verification
  - VAST credentials K8s secret verification
  - VAST storage metrics in VictoriaMetrics
  - VAST syslog configuration and fresh-log verification
"""

import json
import math
import os
import re
import stat
import tempfile
import time
import urllib.parse
from datetime import datetime, timezone

from omnia_auto import read_all_fields, read_yaml_key

from ..vars.common_vars import (
    CFG_KEY_VAST_AUTH_MODE,
    CFG_KEY_VAST_CA_CERT_PATH,
    CFG_KEY_VAST_COLLECTION_TARGETS,
    CFG_KEY_VAST_ENDPOINT,
    CFG_KEY_VAST_LOGS_ENABLED,
    CFG_KEY_VAST_PORT,
    CFG_KEY_VAST_TLS_MODE,
    CMDS,
    MODULE_ROOT,
    SVC_VLAGENT,
    TELEMETRY_NAMESPACE,
    VAST_AUTH_MODES,
    VAST_CREDENTIAL_FIELDS,
    VAST_CREDENTIALS_FILE,
    VAST_CREDENTIALS_KEY_FILE,
    VAST_LOG_APP_NAME,
    VAST_LOG_CLOCK_SKEW_SECONDS,
    VAST_LOG_FIELD_PREVIEW_LENGTH,
    VAST_LOG_QUERY,
    VAST_LOG_QUERY_LIMIT,
    VAST_LOG_MAX_FUTURE_SKEW_SECONDS,
    VAST_LOG_POLL_ATTEMPTS,
    VAST_LOG_POLL_INTERVAL_SECONDS,
    VAST_MAX_METRICS_SHOWN,
    VAST_MAX_CA_FILE_BYTES,
    VAST_MAX_CREDENTIAL_FILE_BYTES,
    VAST_MAX_KEY_FILE_BYTES,
    VAST_MAX_LOG_EVENTS_SHOWN,
    VAST_MAX_STATE_FILE_BYTES,
    VAST_METRIC_FRESHNESS_SECONDS,
    VAST_METRIC_SELECTOR,
    VAST_QUERY_TIMEOUT_SECONDS,
    VAST_REPORT_ID_PATTERN,
    VAST_SCRAPE_HEALTH_QUERY,
    VAST_SCRAPE_SAMPLES_QUERY,
    VAST_SECRET_NAME,
    VAST_SVC_NAME,
    VAST_SYSLOG_PORT_NAME,
    VAST_TLS_MODES,
    VAST_TRIGGER_MAX_AGE_SECONDS,
    VAST_TRIGGER_STATE_FILE,
    VAST_TRIGGER_STATE_SCHEMA_VERSION,
    VAST_TRIGGER_STATE_SUBDIR,
    VAST_VMSCRAPE_NAME,
)
from .vast_api_func import VastApiError, configure_event_notifications
from .telemetry_func import (
    _get_input_path,
    _get_svc_endpoint,
    get_vlselect_endpoint,
    get_vmselect_endpoint,
    load_telemetry_config_from_target,
    run_on_kube_vip,
)


class _VastTriggerStateUnavailable(VastApiError):
    """Raised when the preceding VAST configuration case created no state."""


def _result(success, details=None, error="", **extra):
    """Build a standard VAST verification result."""
    value = {
        "success": success,
        "details": details if details is not None else {},
        "error": error,
    }
    value.update(extra)
    return value


def _utc_timestamp(value):
    """Format an epoch value as ISO-8601 UTC."""
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _query_vm_rows(host, query):
    """Return validated VictoriaMetrics vector rows for one VAST query."""
    ip, port = get_vmselect_endpoint(host)
    if not ip or not port:
        return [], "VictoriaMetrics vmselect endpoint was not found", "", ""

    cmd = CMDS["vast_vm_query_instant"].format(
        vmselect_ip=ip,
        vmselect_port=port,
        query=urllib.parse.quote(query, safe=""),
        timeout=VAST_QUERY_TIMEOUT_SECONDS,
    )
    command_result = run_on_kube_vip(host, cmd)
    if command_result.rc != 0 or not command_result.stdout.strip():
        return [], (
            "VictoriaMetrics query failed "
            f"(rc={command_result.rc})"
        ), ip, port

    try:
        payload = json.loads(command_result.stdout)
    except json.JSONDecodeError:
        return [], "VictoriaMetrics returned invalid JSON", ip, port

    data = payload.get("data") if isinstance(payload, dict) else None
    rows = data.get("result") if isinstance(data, dict) else None
    if not isinstance(payload, dict):
        return [], "VictoriaMetrics returned an invalid response", ip, port
    if payload.get("status") != "success" or not isinstance(rows, list):
        error = payload.get("error", "invalid response shape")
        return [], f"VictoriaMetrics query failed: {error}", ip, port
    return rows, "", ip, port


def _row_value(row):
    """Return a finite numeric value and evaluation timestamp from a row."""
    value = row.get("value") if isinstance(row, dict) else None
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None, None
    try:
        timestamp = float(value[0])
        sample_value = float(value[1])
    except (TypeError, ValueError):
        return None, None
    if not math.isfinite(timestamp) or not math.isfinite(sample_value):
        return None, None
    return sample_value, timestamp


def verify_vast_external_service(host):
    """Verify VAST external headless service exists and has correct endpoint.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, service_name, endpoint_ip, endpoint_port,
        expected_endpoint, expected_port.
    """
    svc_cmd = (
        f"kubectl get svc {VAST_SVC_NAME} -n {TELEMETRY_NAMESPACE}"
        " -o json 2>/dev/null"
    )
    result = run_on_kube_vip(host, svc_cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "service_name": VAST_SVC_NAME,
            "error": "Service not found",
        }

    try:
        svc = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "service_name": VAST_SVC_NAME,
            "error": "JSON parse error",
        }

    svc_port = ""
    for p in svc.get("spec", {}).get("ports", []):
        svc_port = str(p.get("port", ""))
        break

    # Get endpoints
    ep_cmd = (
        f"kubectl get endpoints {VAST_SVC_NAME} -n {TELEMETRY_NAMESPACE}"
        " -o json 2>/dev/null"
    )
    ep_result = run_on_kube_vip(host, ep_cmd)
    endpoint_ip = ""
    endpoint_port = ""
    if ep_result.rc == 0 and ep_result.stdout.strip():
        try:
            ep_data = json.loads(ep_result.stdout)
            for subset in ep_data.get("subsets", []):
                for addr in subset.get("addresses", []):
                    endpoint_ip = addr.get("ip", "")
                    break
                for port in subset.get("ports", []):
                    endpoint_port = str(port.get("port", ""))
                    break
        except json.JSONDecodeError:
            pass

    # Get expected from config
    config = load_telemetry_config_from_target(host)
    expected_endpoint = read_yaml_key(config, CFG_KEY_VAST_ENDPOINT, default="")
    expected_port = str(read_yaml_key(config, CFG_KEY_VAST_PORT, default="443"))

    match = (
        endpoint_ip == expected_endpoint
        and endpoint_port == expected_port
        and svc_port == expected_port
    )

    return {
        "success": match and bool(endpoint_ip),
        "service_name": VAST_SVC_NAME,
        "endpoint_ip": endpoint_ip,
        "endpoint_port": endpoint_port,
        "svc_port": svc_port,
        "expected_endpoint": expected_endpoint,
        "expected_port": expected_port,
    }


def verify_vast_vmscrape(host):
    """Verify VAST VMServiceScrape CR exists.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, name, scrape_interval, port, path.
    """
    cmd = (
        f"kubectl get vmservicescrape {VAST_VMSCRAPE_NAME} -n {TELEMETRY_NAMESPACE}"
        " -o json 2>/dev/null"
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "name": VAST_VMSCRAPE_NAME,
            "error": "Not found",
        }

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "name": VAST_VMSCRAPE_NAME,
            "error": "JSON parse error",
        }

    endpoints = data.get("spec", {}).get("endpoints", [])
    interval = ""
    port = ""
    path = ""
    if endpoints:
        interval = endpoints[0].get("interval", "")
        port = endpoints[0].get("port", "")
        path = endpoints[0].get("path", "/api/prometheusmetrics/all")

    config = load_telemetry_config_from_target(host)
    expected_path = read_yaml_key(
        config,
        "vast_configuration.metrics_path",
        default="/api/prometheusmetrics/all",
    )

    return {
        "success": bool(port) and path == expected_path,
        "name": VAST_VMSCRAPE_NAME,
        "scrape_interval": interval,
        "port": port,
        "path": path,
        "expected_path": expected_path,
    }


def verify_vast_credentials_secret(host):
    """Verify VAST credentials K8s secret exists.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, secret_name, keys_found.
    """
    cmd = (
        f"kubectl get secret {VAST_SECRET_NAME} -n {TELEMETRY_NAMESPACE}"
        " -o json 2>/dev/null"
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "secret_name": VAST_SECRET_NAME,
            "error": "Not found",
        }

    try:
        data = json.loads(result.stdout)
        keys_found = list(data.get("data", {}).keys())
    except json.JSONDecodeError:
        return {
            "success": False,
            "secret_name": VAST_SECRET_NAME,
            "error": "JSON parse",
        }

    return {
        "success": len(keys_found) > 0,
        "secret_name": VAST_SECRET_NAME,
        "keys_found": keys_found,
    }


def verify_vast_metrics(host):
    """Verify the live VAST scrape pipeline and fresh attributed metrics.

    Args:
        host: Testinfra host connection to the OIM.
    Returns:
        Standard result with scrape health, series counts, and metric samples.
    """
    health_rows, error, ip, port = _query_vm_rows(
        host, VAST_SCRAPE_HEALTH_QUERY,
    )
    if error:
        return _result(False, error=error, vmselect_ip=ip, vmselect_port=port)

    healthy_targets = sum(
        1 for row in health_rows if (_row_value(row)[0] or 0) == 1
    )
    if healthy_targets == 0:
        return _result(
            False,
            error="VAST vmagent scrape target is not up",
            vmselect_ip=ip,
            vmselect_port=port,
            healthy_targets=0,
        )

    sample_rows, error, _, _ = _query_vm_rows(
        host, VAST_SCRAPE_SAMPLES_QUERY,
    )
    if error:
        return _result(False, error=error, vmselect_ip=ip, vmselect_port=port)
    scraped_samples = sum(
        value or 0 for value, _ in map(_row_value, sample_rows)
    )
    if scraped_samples <= 0:
        return _result(
            False,
            error="VAST scrape target returned no Prometheus samples",
            vmselect_ip=ip,
            vmselect_port=port,
            healthy_targets=healthy_targets,
            scraped_samples=0,
        )

    timestamp_query = f"timestamp({VAST_METRIC_SELECTOR}) keep_metric_names"
    metric_rows, error, _, _ = _query_vm_rows(host, timestamp_query)
    if error:
        return _result(False, error=error, vmselect_ip=ip, vmselect_port=port)

    metric_samples = []
    metric_names = set()
    for row in metric_rows:
        sample_timestamp, _ = _row_value(row)
        metric = row.get("metric", {}) if isinstance(row, dict) else {}
        metric_name = metric.get("__name__", "")
        if sample_timestamp is None or not metric_name:
            continue
        metric_names.add(metric_name)
        metric_samples.append({
            "metric": metric_name,
            "timestamp": sample_timestamp,
            "timestamp_utc": _utc_timestamp(sample_timestamp),
        })

    if not metric_samples:
        return _result(
            False,
            error=(
                "No source-labelled VAST metrics were found in "
                "VictoriaMetrics"
            ),
            vmselect_ip=ip,
            vmselect_port=port,
            healthy_targets=healthy_targets,
            scraped_samples=int(scraped_samples),
        )

    latest_timestamp = max(item["timestamp"] for item in metric_samples)
    latest_age = max(0.0, time.time() - latest_timestamp)
    fresh = latest_age <= VAST_METRIC_FRESHNESS_SECONDS
    examples = sorted(
        metric_samples,
        key=lambda item: (-item["timestamp"], item["metric"]),
    )[:VAST_MAX_METRICS_SHOWN]
    return _result(
        fresh,
        error=(
            "Latest source-labelled VAST metric is stale "
            f"({latest_age:.0f}s old; maximum "
            f"{VAST_METRIC_FRESHNESS_SECONDS}s)"
            if not fresh else ""
        ),
        vmselect_ip=ip,
        vmselect_port=port,
        healthy_targets=healthy_targets,
        scraped_samples=int(scraped_samples),
        series_count=len(metric_samples),
        metric_count=len(metric_names),
        latest_timestamp=latest_timestamp,
        latest_timestamp_utc=_utc_timestamp(latest_timestamp),
        latest_age_seconds=latest_age,
        metric_details=examples,
    )


def _read_target_file(host, file_path, maximum_bytes):
    """Read one bounded regular file from the execution OIM."""
    remote_file = host.file(file_path)
    if not remote_file.exists or not remote_file.is_file:
        raise VastApiError(f"Required target file is missing: {file_path}")
    if remote_file.is_symlink:
        raise VastApiError(
            f"Required target file must not be a symlink: {file_path}"
        )
    if remote_file.size > maximum_bytes:
        raise VastApiError(
            f"Required target file is unexpectedly large: {file_path}"
        )
    content = remote_file.content
    return content.encode("utf-8") if isinstance(content, str) else content


def _write_sensitive_file(directory, name, content):
    """Write sensitive staging content with owner-only permissions."""
    file_path = os.path.join(directory, name)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    file_descriptor = os.open(file_path, flags, 0o600)
    with os.fdopen(file_descriptor, "wb") as staged_file:
        staged_file.write(content)
        staged_file.flush()
        os.fsync(staged_file.fileno())
    return file_path


def _load_vast_credentials(host, input_path, staging_dir):
    """Load only VAST fields from the target domain credential store."""
    credential_path = f"{input_path}/{VAST_CREDENTIALS_FILE}"
    key_path = f"{input_path}/{VAST_CREDENTIALS_KEY_FILE}"
    credential_content = _read_target_file(
        host, credential_path, VAST_MAX_CREDENTIAL_FILE_BYTES,
    )
    key_content = _read_target_file(
        host, key_path, VAST_MAX_KEY_FILE_BYTES,
    )
    staged_credentials = _write_sensitive_file(
        staging_dir, VAST_CREDENTIALS_FILE, credential_content,
    )
    staged_key = _write_sensitive_file(
        staging_dir, VAST_CREDENTIALS_KEY_FILE, key_content,
    )
    credential_result = read_all_fields(staged_credentials, staged_key)
    if not credential_result.get("success"):
        raise VastApiError("Unable to decrypt Telemetry domain credentials")

    credential_data = credential_result.get("data", {})
    if not isinstance(credential_data, dict):
        raise VastApiError("Telemetry domain credentials have invalid structure")
    username = str(
        credential_data.get(VAST_CREDENTIAL_FIELDS["username"], "")
    ).strip()
    password = str(
        credential_data.get(VAST_CREDENTIAL_FIELDS["password"], "")
    )
    credential_data.clear()
    if not username or not password:
        raise VastApiError(
            "VAST credentials are missing; run "
            "./setup_env.sh --set-domain-creds on the execution OIM"
        )
    return username, password


def _vast_api_context(host, config, staging_dir):
    """Build validated VAST API settings without exposing credentials."""
    endpoint = str(
        read_yaml_key(config, CFG_KEY_VAST_ENDPOINT, default="")
    ).strip()
    auth_mode = str(
        read_yaml_key(config, CFG_KEY_VAST_AUTH_MODE, default="basic")
    ).strip().lower()
    tls_mode = str(
        read_yaml_key(config, CFG_KEY_VAST_TLS_MODE, default="self_signed")
    ).strip().lower()
    if auth_mode not in VAST_AUTH_MODES:
        raise VastApiError(f"Unsupported VAST auth_mode: {auth_mode}")
    if tls_mode not in VAST_TLS_MODES:
        raise VastApiError(f"Unsupported VAST tls_mode: {tls_mode}")

    context = {
        "endpoint": endpoint,
        "port": read_yaml_key(config, CFG_KEY_VAST_PORT, default=443),
        "auth_mode": auth_mode,
        "username": "",
        "password": "",
        "verify_tls": False,
    }
    input_path = _get_input_path(host)
    context["username"], context["password"] = _load_vast_credentials(
        host, input_path, staging_dir,
    )

    if tls_mode == "ca_signed":
        ca_path = str(
            read_yaml_key(config, CFG_KEY_VAST_CA_CERT_PATH, default="")
        ).strip()
        if not ca_path:
            raise VastApiError(
                "vast_ca_cert_path is required when VAST tls_mode is ca_signed"
            )
        if not os.path.isabs(ca_path):
            ca_path = f"{input_path}/{ca_path}"
        ca_content = _read_target_file(
            host, ca_path, VAST_MAX_CA_FILE_BYTES,
        )
        context["verify_tls"] = _write_sensitive_file(
            staging_dir, "vast-ca.crt", ca_content,
        )
    return context


def _trigger_state_path(create_directory=False):
    """Resolve the safe per-run VAST trigger-state path."""
    report_id = os.environ.get("REPORT_ID", "").strip()
    if not re.fullmatch(VAST_REPORT_ID_PATTERN, report_id):
        raise VastApiError(
            "REPORT_ID is missing or invalid; use run_validation.sh so the "
            "VAST trigger and verification share one run identifier"
        )
    state_dir = os.path.join(MODULE_ROOT, VAST_TRIGGER_STATE_SUBDIR)
    if create_directory:
        os.makedirs(state_dir, mode=0o700, exist_ok=True)
        os.chmod(state_dir, 0o700)
    elif os.path.islink(state_dir):
        raise VastApiError("VAST trigger-state directory must not be a symlink")
    return os.path.join(
        state_dir, VAST_TRIGGER_STATE_FILE.format(report_id=report_id),
    )


def _save_trigger_state(state):
    """Atomically persist non-secret correlation data for verify phase."""
    state_path = _trigger_state_path(create_directory=True)
    state_dir = os.path.dirname(state_path)
    file_descriptor, temporary_path = tempfile.mkstemp(
        prefix=".vast-syslog-", dir=state_dir, text=True,
    )
    try:
        os.fchmod(file_descriptor, 0o600)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as state_file:
            file_descriptor = -1
            json.dump(state, state_file, sort_keys=True)
            state_file.flush()
            os.fsync(state_file.fileno())
        os.replace(temporary_path, state_path)
        os.chmod(state_path, 0o600)
    except (OSError, TypeError, ValueError):
        if file_descriptor >= 0:
            try:
                os.close(file_descriptor)
            except OSError:
                pass
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise
    return state_path


def _load_trigger_state():
    """Load and validate non-secret correlation data for this runner ID."""
    state_path = _trigger_state_path()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        file_descriptor = os.open(state_path, flags)
        with os.fdopen(file_descriptor, "r", encoding="utf-8") as state_file:
            file_status = os.fstat(state_file.fileno())
            if (
                    not stat.S_ISREG(file_status.st_mode)
                    or file_status.st_uid != os.getuid()
                    or file_status.st_mode & 0o077
                    or file_status.st_size > VAST_MAX_STATE_FILE_BYTES):
                raise VastApiError(
                    "VAST test-event state has unsafe permissions"
                )
            state = json.load(state_file)
    except FileNotFoundError as exc:
        raise _VastTriggerStateUnavailable(
            "No VAST test-event state exists for this run; verify that the "
            "preceding VAST syslog configuration case completed successfully"
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise VastApiError("VAST test-event state is unreadable") from exc
    if not isinstance(state, dict):
        raise VastApiError("VAST test-event state has invalid structure")
    if state.get("schema_version") != VAST_TRIGGER_STATE_SCHEMA_VERSION:
        raise VastApiError("VAST test-event state has an unsupported version")
    expected_fields = {
        "schema_version",
        "trigger_epoch",
        "vast_endpoint",
        "syslog_host",
        "syslog_port",
        "syslog_protocol",
    }
    if set(state) != expected_fields:
        raise VastApiError("VAST test-event state has unexpected fields")
    if (
            not isinstance(state.get("vast_endpoint"), str)
            or not state["vast_endpoint"]
            or not isinstance(state.get("syslog_host"), str)
            or not state["syslog_host"]
            or isinstance(state.get("syslog_port"), bool)
            or not isinstance(state.get("syslog_port"), int)
            or not 1 <= state["syslog_port"] <= 65535
            or state.get("syslog_protocol") != "tcp"):
        raise VastApiError("VAST test-event state has invalid values")
    return state, state_path


def _remove_trigger_state(state_path):
    """Remove consumed correlation state without following links."""
    try:
        os.unlink(state_path)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise VastApiError("Unable to remove VAST test-event state") from exc


def configure_vast_syslog_and_trigger(host):
    """Configure VAST syslog from target inputs and emit a test event."""
    config = load_telemetry_config_from_target(host)
    if not read_yaml_key(config, CFG_KEY_VAST_LOGS_ENABLED, default=False):
        return _result(
            True,
            details={"reason": "VAST logs are disabled"},
            skipped=True,
        )
    collection_targets = read_yaml_key(
        config, CFG_KEY_VAST_COLLECTION_TARGETS, default=[],
    )
    if (
            not isinstance(collection_targets, list)
            or "victoria_logs" not in collection_targets):
        return _result(
            False,
            error=(
                "VAST logs are enabled but collection_targets does not "
                "include victoria_logs"
            ),
        )

    syslog_host, syslog_port = _get_svc_endpoint(
        host, SVC_VLAGENT, VAST_SYSLOG_PORT_NAME,
    )
    if not syslog_host or not syslog_port:
        return _result(
            False,
            error="VLAgent syslog LoadBalancer endpoint was not found",
        )

    context = {}
    try:
        with tempfile.TemporaryDirectory(prefix="omnia_vast_api_") as staging:
            os.chmod(staging, 0o700)
            context = _vast_api_context(host, config, staging)
            api_result = configure_event_notifications(
                context, syslog_host, syslog_port,
            )
        trigger_time = _utc_timestamp(api_result["trigger_epoch"])
        _save_trigger_state({
            "schema_version": VAST_TRIGGER_STATE_SCHEMA_VERSION,
            "trigger_epoch": api_result["trigger_epoch"],
            "vast_endpoint": str(context.get("endpoint", "")),
            "syslog_host": api_result["syslog_host"],
            "syslog_port": api_result["syslog_port"],
            "syslog_protocol": api_result["syslog_protocol"],
        })
    except (OSError, RuntimeError, TypeError, ValueError, VastApiError) as exc:
        return _result(False, error=str(exc))
    finally:
        context["username"] = ""
        context["password"] = ""

    return _result(
        True,
        details={
            "vast_endpoint": context["endpoint"],
            "syslog_target": (
                f"{api_result['syslog_host']}:{api_result['syslog_port']}"
            ),
            "syslog_protocol": api_result["syslog_protocol"],
            "configuration": (
                "updated" if api_result["changed"] else "already matched"
            ),
            "readback_http_status": api_result["readback_status"],
            "trigger_http_status": api_result["trigger_status"],
            "trigger_time_utc": trigger_time,
        },
    )


def _parse_log_timestamp(value):
    """Parse a VictoriaLogs timestamp into Unix epoch seconds."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    timestamp = str(value or "").strip()
    if not timestamp:
        return None
    try:
        return float(timestamp)
    except ValueError:
        pass
    normalized = timestamp.replace("Z", "+00:00")
    fraction = re.search(r"\.(\d{7,})(?=[+-]\d\d:\d\d$)", normalized)
    if fraction:
        normalized = (
            normalized[:fraction.start(1)]
            + fraction.group(1)[:6]
            + normalized[fraction.end(1):]
        )
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _fresh_vast_entries(output, lower_bound, upper_bound):
    """Return VAST events inside the trigger-correlated time window."""
    entries = []
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise VastApiError(
                "VictoriaLogs returned a malformed JSON log record"
            ) from exc
        if not isinstance(entry, dict):
            continue
        app_name = str(entry.get("app_name", ""))
        timestamp = _parse_log_timestamp(entry.get("_time"))
        if (
            app_name == VAST_LOG_APP_NAME
            and timestamp is not None
            and lower_bound <= timestamp <= upper_bound
        ):
            entries.append(_vast_event_summary(entry, timestamp))
    return entries


def _bounded_vast_log_field(value):
    """Return one safe, single-line VAST log field for report output."""
    normalized = " ".join(str(value or "").split())
    if len(normalized) <= VAST_LOG_FIELD_PREVIEW_LENGTH:
        return normalized
    return f"{normalized[:VAST_LOG_FIELD_PREVIEW_LENGTH - 3]}..."


def _vast_event_summary(entry, timestamp):
    """Extract allowlisted RFC5424 fields from one VAST event."""
    return {
        "timestamp": timestamp,
        "timestamp_utc": _utc_timestamp(timestamp),
        "hostname": _bounded_vast_log_field(entry.get("hostname")),
        "app_name": _bounded_vast_log_field(entry.get("app_name")),
        "process": _bounded_vast_log_field(entry.get("proc_id")),
        "severity": _bounded_vast_log_field(
            entry.get("level") or entry.get("severity")
        ),
        "facility": _bounded_vast_log_field(
            entry.get("facility_keyword") or entry.get("facility")
        ),
        "format": _bounded_vast_log_field(entry.get("format")),
    }


def _validated_trigger_state(host):
    """Return a fresh trigger state that matches the current VAST endpoint."""
    state, state_path = _load_trigger_state()
    try:
        trigger_epoch = float(state.get("trigger_epoch"))
    except (TypeError, ValueError) as exc:
        raise VastApiError("VAST trigger timestamp is invalid") from exc
    if not math.isfinite(trigger_epoch):
        raise VastApiError("VAST trigger timestamp is invalid")

    age = time.time() - trigger_epoch
    if age < -VAST_LOG_MAX_FUTURE_SKEW_SECONDS:
        raise VastApiError("VAST trigger timestamp is in the future")
    if age > VAST_TRIGGER_MAX_AGE_SECONDS:
        raise VastApiError(
            "VAST test-event state is stale; rerun the VAST verification"
        )

    current = get_vast_endpoint_from_config(host)
    if str(current.get("endpoint", "")).strip() != state.get("vast_endpoint"):
        raise VastApiError(
            "VAST endpoint changed after the test event was triggered"
        )
    return trigger_epoch, state_path


def _query_fresh_vast_entries(
        host, vlselect_ip, vlselect_port, query_start, lower_bound):
    """Query VictoriaLogs once for trigger-correlated VAST events."""
    command = CMDS["vast_vl_query_logs"].format(
        vlselect_ip=vlselect_ip,
        vlselect_port=vlselect_port,
        query=urllib.parse.quote(VAST_LOG_QUERY, safe=""),
        limit=VAST_LOG_QUERY_LIMIT,
        start=urllib.parse.quote(query_start, safe=""),
        timeout=VAST_QUERY_TIMEOUT_SECONDS,
    )
    result = run_on_kube_vip(host, command)
    if result.rc != 0:
        raise VastApiError(f"VictoriaLogs query failed (rc={result.rc})")
    return _fresh_vast_entries(
        result.stdout,
        lower_bound,
        time.time() + VAST_LOG_MAX_FUTURE_SKEW_SECONDS,
    )


def _vast_log_details(entries, trigger_epoch, query_start, attempt):
    """Build bounded, structured report details for matched VAST events."""
    ordered_entries = sorted(entries, key=lambda entry: entry["timestamp"])
    shown_events = list(reversed(
        ordered_entries[-VAST_MAX_LOG_EVENTS_SHOWN:]
    ))
    return {
        "trigger_time_utc": _utc_timestamp(trigger_epoch),
        "query_start_utc": query_start,
        "matched_events": len(entries),
        "earliest_event_utc": ordered_entries[0]["timestamp_utc"],
        "latest_event_utc": ordered_entries[-1]["timestamp_utc"],
        "latest_event_age_seconds": max(
            0.0, time.time() - ordered_entries[-1]["timestamp"]
        ),
        "source_hosts": sorted({
            entry["hostname"] for entry in ordered_entries if entry["hostname"]
        }),
        "event_summaries": [
            {
                key: value
                for key, value in event.items()
                if key != "timestamp"
            }
            for event in shown_events
        ],
        "remaining_events": len(entries) - len(shown_events),
        "query_limit_reached": len(entries) >= VAST_LOG_QUERY_LIMIT,
        "poll_attempt": attempt,
    }


def verify_fresh_vast_test_event(host):
    """Verify the VAST test event from this run reached VictoriaLogs."""
    try:
        trigger_epoch, state_path = _validated_trigger_state(host)
    except _VastTriggerStateUnavailable as exc:
        return _result(False, error=str(exc), count=0)
    except VastApiError as exc:
        return _result(False, error=str(exc), count=0)

    ip, port = get_vlselect_endpoint(host)
    if not ip or not port:
        try:
            _remove_trigger_state(state_path)
        except VastApiError as exc:
            return _result(False, error=str(exc), count=0)
        return _result(
            False,
            error="VictoriaLogs vlselect endpoint was not found",
            count=0,
        )

    lower_bound = trigger_epoch - VAST_LOG_CLOCK_SKEW_SECONDS
    query_start = datetime.fromtimestamp(
        lower_bound, tz=timezone.utc,
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    last_error = "No fresh VAST test event was found in VictoriaLogs"
    for attempt in range(1, VAST_LOG_POLL_ATTEMPTS + 1):
        try:
            entries = _query_fresh_vast_entries(
                host, ip, port, query_start, lower_bound,
            )
        except VastApiError as exc:
            last_error = str(exc)
        else:
            if entries:
                try:
                    _remove_trigger_state(state_path)
                except VastApiError as exc:
                    return _result(False, error=str(exc), count=0)
                return _result(
                    True,
                    details=_vast_log_details(
                        entries, trigger_epoch, query_start, attempt,
                    ),
                    count=len(entries),
                    vlselect_ip=ip,
                    vlselect_port=port,
                )
            last_error = "No fresh VAST test event was found in VictoriaLogs"
        if attempt < VAST_LOG_POLL_ATTEMPTS:
            time.sleep(VAST_LOG_POLL_INTERVAL_SECONDS)

    try:
        _remove_trigger_state(state_path)
    except VastApiError as exc:
        last_error = str(exc)
    return _result(
        False,
        details={
            "trigger_time_utc": _utc_timestamp(trigger_epoch),
            "query_start_utc": query_start,
            "poll_attempts": VAST_LOG_POLL_ATTEMPTS,
        },
        error=last_error,
        count=0,
        vlselect_ip=ip,
        vlselect_port=port,
    )


def get_vast_endpoint_from_config(host):
    """Get VAST endpoint from telemetry config.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict with keys: success, endpoint, port, metrics_path.
    """
    config = load_telemetry_config_from_target(host)
    endpoint = read_yaml_key(config, CFG_KEY_VAST_ENDPOINT, default="")
    port = read_yaml_key(config, CFG_KEY_VAST_PORT, default=443)
    metrics_path = read_yaml_key(
        config, "vast_configuration.metrics_path",
        default="/api/prometheusmetrics/all"
    )
    auth_mode = read_yaml_key(config, CFG_KEY_VAST_AUTH_MODE, default="basic")

    return {
        "success": bool(endpoint),
        "endpoint": endpoint,
        "port": str(port),
        "metrics_path": metrics_path,
        "auth_mode": auth_mode,
    }
