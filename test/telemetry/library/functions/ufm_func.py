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
UFM — Module-Specific Verification Functions.

Handles:
  - UFM external headless service verification
  - UFM VMServiceScrape CR verification
  - UFM credentials K8s secret verification
  - UFM InfiniBand metrics in VictoriaMetrics
"""

import json
import math
from datetime import datetime, timezone

from omnia_auto import read_yaml_key

from ..messages.ufm_msgs import UFM_DETAIL_MSGS, UFM_ERROR_MSGS
from ..vars.common_vars import TELEMETRY_NAMESPACE
from ..vars.ufm_vars import (
    CFG_KEY_UFM_ENDPOINT,
    CFG_KEY_UFM_PORT,
    UFM_CMD_TEMPLATES,
    UFM_DEFAULT_METRICS_PATH,
    UFM_DEFAULT_METRICS_PORT,
    UFM_SVC_NAME,
    UFM_SECRET_NAME,
    UFM_UTC_TIMESTAMP_FORMAT,
    UFM_VMSCRAPE_NAME,
)
from .telemetry_func import (
    load_telemetry_config_from_target,
    run_on_kube_vip,
    query_vm_metric_names,
    query_vm_instant,
)


def verify_ufm_external_service(host):
    """Verify UFM external headless service exists and has correct endpoint.

    Returns:
        dict with keys: success, service_name, endpoint_ip, endpoint_port,
        expected_endpoint, expected_port.
    """
    svc_cmd = UFM_CMD_TEMPLATES["get_service_json"].format(
        name=UFM_SVC_NAME,
        namespace=TELEMETRY_NAMESPACE,
    )
    result = run_on_kube_vip(host, svc_cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "service_name": UFM_SVC_NAME,
            "error": UFM_ERROR_MSGS["service_not_found"],
        }

    try:
        svc = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "service_name": UFM_SVC_NAME,
            "error": UFM_ERROR_MSGS["service_json_invalid"],
        }

    svc_port = ""
    for port_spec in svc.get("spec", {}).get("ports", []):
        svc_port = str(port_spec.get("port", ""))
        break

    # Get endpoints
    ep_cmd = UFM_CMD_TEMPLATES["get_endpoints_json"].format(
        name=UFM_SVC_NAME,
        namespace=TELEMETRY_NAMESPACE,
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
            return {
                "success": False,
                "service_name": UFM_SVC_NAME,
                "error": UFM_ERROR_MSGS["endpoints_json_invalid"],
            }

    # Get expected from config
    config = load_telemetry_config_from_target(host)
    expected_endpoint = read_yaml_key(config, CFG_KEY_UFM_ENDPOINT, default="")
    expected_port = str(
        read_yaml_key(
            config,
            CFG_KEY_UFM_PORT,
            default=UFM_DEFAULT_METRICS_PORT,
        )
    )

    match = endpoint_ip == expected_endpoint

    return {
        "success": match and bool(endpoint_ip),
        "service_name": UFM_SVC_NAME,
        "endpoint_ip": endpoint_ip,
        "endpoint_port": endpoint_port,
        "svc_port": svc_port,
        "expected_endpoint": expected_endpoint,
        "expected_port": expected_port,
    }


def verify_ufm_vmscrape(host):
    """Verify UFM VMServiceScrape CR exists.

    Returns:
        dict with keys: success, name, scrape_interval, port, path.
    """
    cmd = UFM_CMD_TEMPLATES["get_vmscrape_json"].format(
        name=UFM_VMSCRAPE_NAME,
        namespace=TELEMETRY_NAMESPACE,
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "name": UFM_VMSCRAPE_NAME,
            "error": UFM_ERROR_MSGS["vmscrape_not_found"],
        }

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "name": UFM_VMSCRAPE_NAME,
            "error": UFM_ERROR_MSGS["vmscrape_json_invalid"],
        }

    endpoints = data.get("spec", {}).get("endpoints", [])
    interval = ""
    port = ""
    path = ""
    if endpoints:
        interval = endpoints[0].get("interval", "")
        port = endpoints[0].get("port", "")
        path = endpoints[0].get("path", UFM_DEFAULT_METRICS_PATH)

    return {
        "success": True,
        "name": UFM_VMSCRAPE_NAME,
        "scrape_interval": interval,
        "port": port,
        "path": path,
    }


def verify_ufm_credentials_secret(host):
    """Verify UFM credentials K8s secret exists.

    Returns:
        dict with keys: success, secret_name, keys_found.
    """
    cmd = UFM_CMD_TEMPLATES["get_secret_json"].format(
        name=UFM_SECRET_NAME,
        namespace=TELEMETRY_NAMESPACE,
    )
    result = run_on_kube_vip(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {
            "success": False,
            "secret_name": UFM_SECRET_NAME,
            "error": UFM_ERROR_MSGS["secret_not_found"],
        }

    try:
        data = json.loads(result.stdout)
        keys_found = list(data.get("data", {}).keys())
    except json.JSONDecodeError:
        return {
            "success": False,
            "secret_name": UFM_SECRET_NAME,
            "error": UFM_ERROR_MSGS["secret_json_invalid"],
        }

    return {
        "success": len(keys_found) > 0,
        "secret_name": UFM_SECRET_NAME,
        "keys_found": keys_found,
    }


def _live_metric_samples(results):
    """Return query results containing a finite timestamp and sample value."""
    samples = []
    for result in results:
        if not isinstance(result, dict):
            continue
        value = result.get("value")
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            continue
        try:
            timestamp = float(value[0])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(timestamp) or timestamp <= 0 or value[1] is None:
            continue
        samples.append({
            "timestamp": timestamp,
            "value": value[1],
        })
    return samples


def _utc_timestamp(timestamp):
    """Format an epoch timestamp for deterministic UTC test output."""
    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).strftime(UFM_UTC_TIMESTAMP_FORMAT)


def _format_metric_results(metric_results):
    """Format every expected metric as an ordered pass or fail row."""
    lines = []
    for metric_result in metric_results:
        if metric_result["found"]:
            lines.append(
                UFM_DETAIL_MSGS["metric_found"].format(
                    metric=metric_result["metric"],
                    sample_count=metric_result["sample_count"],
                    value=metric_result["value"],
                    timestamp_utc=metric_result["timestamp_utc"],
                )
            )
            continue
        reason_key = (
            "metric_sample_missing"
            if metric_result["name_found"]
            else "metric_name_missing"
        )
        lines.append(
            UFM_DETAIL_MSGS["metric_missing"].format(
                metric=metric_result["metric"],
                reason=UFM_DETAIL_MSGS[reason_key],
            )
        )
    return "\n".join(lines)


def _format_metrics_details(result):
    """Build centralized UFM metrics counts and per-metric details."""
    return UFM_DETAIL_MSGS["metrics"].format(
        expected_count=result["expected_metric_count"],
        found_count=result["found_metric_count"],
        missing_metrics=result["missing"],
        metric_results=_format_metric_results(result["metric_results"]),
    )


def verify_ufm_metrics(host, expected_metrics):
    """Verify UFM InfiniBand metrics exist in VictoriaMetrics.

    Args:
        host: Testinfra host connection to the OIM.
        expected_metrics: List of metric names to check.

    Returns:
        dict containing ordered metric results and expected/found/missing counts.
    """
    expected = list(expected_metrics)
    all_names = set(query_vm_metric_names(host))
    found = []
    missing = []
    metric_results = []

    for metric in expected:
        name_found = metric in all_names
        samples = (
            _live_metric_samples(query_vm_instant(host, metric))
            if name_found
            else []
        )
        if not samples:
            missing.append(metric)
            metric_results.append({
                "metric": metric,
                "found": False,
                "name_found": name_found,
                "sample_count": 0,
                "value": None,
                "timestamp": None,
                "timestamp_utc": "",
            })
            continue

        latest = max(samples, key=lambda sample: sample["timestamp"])
        found.append(metric)
        metric_results.append({
            "metric": metric,
            "found": True,
            "name_found": True,
            "sample_count": len(samples),
            "value": latest["value"],
            "timestamp": latest["timestamp"],
            "timestamp_utc": _utc_timestamp(latest["timestamp"]),
        })

    result = {
        "success": not missing,
        "expected": expected,
        "expected_metric_count": len(expected),
        "found": found,
        "found_metric_count": len(found),
        "missing": missing,
        "missing_metric_count": len(missing),
        "metric_results": metric_results,
        # Retain the historical key for callers that consume successful rows.
        "metric_details": [
            result for result in metric_results if result["found"]
        ],
    }
    result["details"] = _format_metrics_details(result)
    return result
