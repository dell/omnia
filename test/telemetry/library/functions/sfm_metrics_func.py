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

"""SFM-to-VictoriaMetrics three-metric timestamp verification helpers."""

import json
import math
import time
import urllib.parse
from datetime import datetime, timezone

from ..messages.sfm_msgs import SFM_DETAIL_MSGS, SFM_ERROR_MSGS
from ..vars.sfm_vars import (
    SFM_CMD_TEMPLATES,
    SFM_EXPECTED_METRICS,
    SFM_MAX_METRIC_AGE_SECONDS,
    SFM_METRIC_IDENTITY_LABELS,
    SFM_METRIC_QUERY_TIMEOUT_SECONDS,
    SFM_METRIC_RANGE_STEP_SECONDS,
    SFM_METRIC_RANGE_WINDOW_SECONDS,
    SFM_TIMESTAMP_QUERY_TEMPLATE,
    SFM_VM_POLL_ATTEMPTS,
    SFM_VM_POLL_INTERVAL_SECONDS,
)
from .sfm_func import load_sfm_context, sfm_result, sfm_skip_result
from .telemetry_func import get_vmselect_endpoint, run_on_kube_vip


class _SfmMetricError(RuntimeError):
    """Safe error raised by SFM VictoriaMetrics verification."""


def _utc_timestamp(value):
    """Format an epoch timestamp as a UTC ISO-8601 string."""
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _display_timestamp(value):
    """Format an epoch timestamp for compact UTC console output."""
    return datetime.fromtimestamp(
        value, tz=timezone.utc,
    ).strftime("%Y-%m-%d %H:%M:%S UTC")


def _query_range_rows(host, endpoint, query, start, end):
    """Return validated matrix rows for one VictoriaMetrics range query."""
    encoded_query = urllib.parse.quote(query, safe="")
    command = SFM_CMD_TEMPLATES["vm_query_range"].format(
        vmselect_ip=endpoint["ip"],
        vmselect_port=endpoint["port"],
        query=encoded_query,
        start=start,
        end=end,
        step=SFM_METRIC_RANGE_STEP_SECONDS,
        timeout=SFM_METRIC_QUERY_TIMEOUT_SECONDS,
    )
    command_result = run_on_kube_vip(host, command)
    if command_result.rc != 0 or not command_result.stdout.strip():
        raise _SfmMetricError(
            SFM_ERROR_MSGS["vm_query_failed"].format(query=query)
        )
    try:
        payload = json.loads(command_result.stdout)
    except json.JSONDecodeError as exc:
        raise _SfmMetricError(
            SFM_ERROR_MSGS["vm_query_json_invalid"].format(error=exc)
        ) from exc
    data = payload.get("data") if isinstance(payload, dict) else None
    rows = data.get("result") if isinstance(data, dict) else None
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "success"
        or not isinstance(rows, list)
        or any(not isinstance(row, dict) for row in rows)
    ):
        raise _SfmMetricError(SFM_ERROR_MSGS["vm_query_shape_invalid"])
    return rows


def _identity(labels):
    """Return one complete attributable series identity from metric labels."""
    if not isinstance(labels, dict):
        return None
    if any(not labels.get(name) for name in SFM_METRIC_IDENTITY_LABELS):
        return None
    normalized = {
        name: str(labels[name]) for name in SFM_METRIC_IDENTITY_LABELS
    }
    return tuple(sorted(normalized.items()))


def _matrix_samples(row):
    """Return finite evaluation-time and sample-value pairs from a row."""
    values = row.get("values")
    if not isinstance(values, list):
        return []
    samples = []
    for value in values:
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            continue
        try:
            evaluation_time = float(value[0])
            sample_value = float(value[1])
        except (TypeError, ValueError):
            continue
        if math.isfinite(evaluation_time) and math.isfinite(sample_value):
            samples.append((evaluation_time, sample_value))
    return samples


def _rows_by_identity(rows):
    """Map complete SFM label identities to one validated matrix row."""
    mapped = {}
    for row in rows:
        identity = _identity(row.get("metric"))
        if identity is not None and _matrix_samples(row):
            mapped[identity] = row
    return mapped


def _paired_samples(value_row, timestamp_row, start, end):
    """Pair raw values with original timestamps from ``timestamp()``."""
    values = dict(_matrix_samples(value_row))
    samples = []
    for evaluation_time, original_timestamp in _matrix_samples(timestamp_row):
        if original_timestamp < start or original_timestamp > end:
            continue
        if evaluation_time not in values:
            continue
        samples.append({
            "timestamp": original_timestamp,
            "value": values[evaluation_time],
        })
    return sorted(samples, key=lambda sample: sample["timestamp"])


def _metric_data(host, endpoint, metric, start, end):
    """Return attributable earliest/latest series data for one metric."""
    value_rows = _query_range_rows(host, endpoint, metric, start, end)
    timestamp_query = SFM_TIMESTAMP_QUERY_TEMPLATE.format(selector=metric)
    timestamp_rows = _query_range_rows(
        host, endpoint, timestamp_query, start, end,
    )
    values_by_identity = _rows_by_identity(value_rows)
    timestamps_by_identity = _rows_by_identity(timestamp_rows)
    usable = {}
    for identity in set(values_by_identity).intersection(
        timestamps_by_identity,
    ):
        samples = _paired_samples(
            values_by_identity[identity],
            timestamps_by_identity[identity],
            start,
            end,
        )
        if samples:
            usable[identity] = samples
    return {
        "metric": metric,
        "series_count": len(values_by_identity),
        "series": usable,
    }


def _common_identity(metric_data):
    """Choose the freshest complete series identity shared by all metrics."""
    identity_sets = [set(value["series"]) for value in metric_data]
    if not identity_sets:
        return None
    common = set.intersection(*identity_sets)
    if not common:
        return None
    return max(
        common,
        key=lambda identity: (
            min(
                value["series"][identity][-1]["timestamp"]
                for value in metric_data
            ),
            identity,
        ),
    )


def _metric_result(value, identity, current_time):
    """Build one structured earliest/latest result for a shared identity."""
    samples = value["series"][identity]
    earliest = samples[0]
    latest = samples[-1]
    return {
        "metric": value["metric"],
        "series_count": value["series_count"],
        "labels": dict(identity),
        "earliest": {
            **earliest,
            "timestamp_utc": _utc_timestamp(earliest["timestamp"]),
        },
        "latest": {
            **latest,
            "timestamp_utc": _utc_timestamp(latest["timestamp"]),
            "age": max(0.0, current_time - latest["timestamp"]),
        },
    }


def _collect_metric_results(host, endpoint, start, end):
    """Collect three metrics and return a common attributed series result."""
    all_data = [
        _metric_data(host, endpoint, metric, start, end)
        for metric in SFM_EXPECTED_METRICS
    ]
    found = [
        value["metric"] for value in all_data if value["series_count"] > 0
    ]
    missing = [
        metric for metric in SFM_EXPECTED_METRICS if metric not in found
    ]
    if missing:
        raise _SfmMetricError(
            SFM_ERROR_MSGS["vm_expected_metrics_missing"].format(
                metrics=", ".join(missing),
            )
        )
    identity = _common_identity(all_data)
    if identity is None:
        raise _SfmMetricError(SFM_ERROR_MSGS["vm_common_identity_missing"])
    current_time = time.time()
    metric_results = [
        _metric_result(value, identity, current_time)
        for value in all_data
    ]
    stale = [
        value["metric"] for value in metric_results
        if value["latest"]["age"] > SFM_MAX_METRIC_AGE_SECONDS
    ]
    if stale:
        raise _SfmMetricError(
            SFM_ERROR_MSGS["vm_metrics_stale"].format(
                metrics=", ".join(stale),
            )
        )
    return dict(identity), found, missing, metric_results


def _metrics_details(
    endpoint, start, end, labels, found, missing, metric_results,
):
    """Build centralized human-readable details for the three metrics."""
    metric_lines = [
        SFM_DETAIL_MSGS["metric_result_line"].format(
            metric=value["metric"],
            series_count=value["series_count"],
            earliest_display=_display_timestamp(
                value["earliest"]["timestamp"],
            ),
            earliest_value=value["earliest"]["value"],
            latest_display=_display_timestamp(
                value["latest"]["timestamp"],
            ),
            latest_value=value["latest"]["value"],
            age=value["latest"]["age"],
        )
        for value in metric_results
    ]
    return SFM_DETAIL_MSGS["metrics_ready"].format(
        vmselect_ip=endpoint["ip"],
        vmselect_port=endpoint["port"],
        expected_metrics=list(SFM_EXPECTED_METRICS),
        found=len(found),
        expected=len(SFM_EXPECTED_METRICS),
        missing_metrics=missing,
        window_seconds=SFM_METRIC_RANGE_WINDOW_SECONDS,
        start_display=_display_timestamp(start),
        end_display=_display_timestamp(end),
        switch_id=labels["switch_id"],
        interface_name=labels["interface_name"],
        series_labels=", ".join(
            f"{name}={value}" for name, value in sorted(labels.items())
        ),
        metric_results="\n".join(metric_lines),
    )


def verify_sfm_metrics_in_victoria(host):
    """Verify three fresh SFM metrics share one Victoria series identity.

    Args:
        host: Testinfra connection used to query VictoriaMetrics.

    Returns:
        Standard result with query window, labels, and earliest/latest values.
    """
    try:
        if load_sfm_context() is None:
            return sfm_skip_result()
        vmselect_ip, vmselect_port = get_vmselect_endpoint(host)
        if not vmselect_ip or not vmselect_port:
            raise _SfmMetricError(SFM_ERROR_MSGS["vm_endpoint_missing"])
        endpoint = {"ip": vmselect_ip, "port": vmselect_port}
        last_error = None
        for attempt in range(1, SFM_VM_POLL_ATTEMPTS + 1):
            end = time.time()
            start = end - SFM_METRIC_RANGE_WINDOW_SECONDS
            try:
                labels, found, missing, results = _collect_metric_results(
                    host, endpoint, start, end,
                )
                details = _metrics_details(
                    endpoint, start, end, labels, found, missing, results,
                )
                return sfm_result(
                    True,
                    details=details,
                    window={
                        "start": start,
                        "end": end,
                        "seconds": SFM_METRIC_RANGE_WINDOW_SECONDS,
                    },
                    identity_labels=labels,
                    expected_metrics=list(SFM_EXPECTED_METRICS),
                    expected_metric_count=len(SFM_EXPECTED_METRICS),
                    found_metrics=found,
                    found_metric_count=len(found),
                    missing_metrics=missing,
                    metric_results=results,
                )
            except _SfmMetricError as exc:
                last_error = exc
                if attempt < SFM_VM_POLL_ATTEMPTS:
                    time.sleep(SFM_VM_POLL_INTERVAL_SECONDS)
        raise last_error or _SfmMetricError(
            SFM_ERROR_MSGS["vm_metrics_unknown_failure"]
        )
    except (OSError, ValueError, _SfmMetricError) as exc:
        return sfm_result(False, error=str(exc))
