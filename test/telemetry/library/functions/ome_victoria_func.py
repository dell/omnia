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

"""OME-to-VictoriaMetrics and OME-to-VictoriaLogs verification helpers."""

import json
import math
import time
import urllib.parse
from datetime import datetime, timezone

from ..messages.ome_msgs import OME_DETAIL_MSGS, OME_ERROR_MSGS
from ..vars.ome_vars import (
    OME_CMD_TEMPLATES,
    OME_TIMESTAMP_QUERY_TEMPLATE,
    OME_VICTORIA_LOG_TOPICS,
    OME_VICTORIA_METRIC_TOPICS,
    OME_VICTORIA_POLL_INTERVAL_SECONDS,
    OME_VICTORIA_POLL_TIMEOUT_SECONDS,
    OME_VICTORIA_QUERY_TIMEOUT_SECONDS,
    OME_VL_DISPLAY_FIELDS,
    OME_VL_FIELD_VALUE_PREVIEW_LENGTH,
    OME_VL_QUERY_LIMIT,
    OME_VL_RANGE,
    OME_VM_RANGE_STEP_SECONDS,
    OME_VM_RANGE_WINDOW_SECONDS,
)
from .ome_func import get_ome_pipeline_context
from .telemetry_func import (
    get_vlselect_endpoint,
    get_vmselect_endpoint,
    run_on_kube_vip,
)


class _OmeVictoriaError(RuntimeError):
    """Safe error raised by OME Victoria sink verification."""


def _result(success, details="", error="", **extra):
    """Build a standard verification result dictionary."""
    value = {
        "success": success,
        "details": details,
        "error": error,
    }
    value.update(extra)
    return value


def _display_timestamp(value):
    """Format an epoch timestamp as compact UTC text."""
    return datetime.fromtimestamp(
        value,
        tz=timezone.utc,
    ).strftime("%Y-%m-%d %H:%M:%S UTC")


def _utc_timestamp(value):
    """Format an epoch timestamp as an ISO-8601 UTC value."""
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _promql_value(value):
    """Escape one string used in a PromQL label matcher."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _logsql_value(value):
    """Escape one string used in a VictoriaLogs exact field matcher."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _resolved_topic(topic, identifier):
    """Apply the configured OME identifier to a supported topic suffix."""
    suffix = str(topic).rsplit(".", maxsplit=1)[-1]
    return f"{identifier}.{suffix}"


def _pipeline_context(host, pipeline):
    """Return OME source/bridge enablement and configured identifier."""
    context = get_ome_pipeline_context(host)
    if not context["config_valid"]:
        raise _OmeVictoriaError(
            OME_ERROR_MSGS["pipeline_disabled"].format(data_type=pipeline)
        )
    prefix = "metrics" if pipeline == "metrics" else "logs"
    return {
        "source_enabled": context[f"source_{prefix}_enabled"],
        "bridge_enabled": context[f"bridge_{prefix}_enabled"],
        "identifier": context["identifier"],
    }


def _disabled_result(pipeline, topic, context):
    """Return a standard skip result for an intentionally disabled path."""
    return _result(
        True,
        details=OME_DETAIL_MSGS["pipeline_disabled"].format(
            data_type=pipeline,
        ),
        skipped=True,
        pipeline=pipeline,
        topic=topic,
        source_enabled=context["source_enabled"],
        bridge_enabled=context["bridge_enabled"],
    )


def _query_range_rows(host, endpoint, topic, query, start, end):
    """Return validated VictoriaMetrics matrix rows for one query."""
    command = OME_CMD_TEMPLATES["vm_query_range"].format(
        vmselect_ip=endpoint["ip"],
        vmselect_port=endpoint["port"],
        query=urllib.parse.quote(query, safe=""),
        start=start,
        end=end,
        step=OME_VM_RANGE_STEP_SECONDS,
        timeout=OME_VICTORIA_QUERY_TIMEOUT_SECONDS,
    )
    command_result = run_on_kube_vip(host, command)
    if command_result.rc != 0 or not command_result.stdout.strip():
        raise _OmeVictoriaError(
            OME_ERROR_MSGS["vm_query_failed"].format(topic=topic)
        )
    try:
        payload = json.loads(command_result.stdout)
    except json.JSONDecodeError as exc:
        raise _OmeVictoriaError(
            OME_ERROR_MSGS["vm_query_json_invalid"].format(error=exc)
        ) from exc

    data = payload.get("data") if isinstance(payload, dict) else None
    rows = data.get("result") if isinstance(data, dict) else None
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "success"
        or not isinstance(rows, list)
        or any(not isinstance(row, dict) for row in rows)
    ):
        raise _OmeVictoriaError(OME_ERROR_MSGS["vm_query_shape_invalid"])
    return rows


def _labels(row):
    """Return normalized string labels from a VictoriaMetrics row."""
    labels = row.get("metric")
    if not isinstance(labels, dict):
        return {}
    return {str(name): str(value) for name, value in labels.items()}


def _identity(row, include_metric_name=True):
    """Return a stable series identity for a VictoriaMetrics matrix row."""
    labels = _labels(row)
    if not include_metric_name:
        labels.pop("__name__", None)
    return tuple(sorted(labels.items())) if labels else None


def _matrix_samples(row):
    """Return finite evaluation-time and value pairs from a matrix row."""
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
            samples.append((round(evaluation_time, 6), sample_value))
    return samples


def _timestamp_rows_by_identity(rows):
    """Index timestamp-query rows by exact and metric-name-free identity."""
    exact = {}
    without_name = {}
    for row in rows:
        if not _matrix_samples(row):
            continue
        exact_identity = _identity(row)
        if exact_identity is not None:
            exact[exact_identity] = row
        base_identity = _identity(row, include_metric_name=False)
        if base_identity is not None:
            without_name.setdefault(base_identity, []).append(row)
    return exact, without_name


def _matching_timestamp_row(value_row, exact, without_name):
    """Return the unambiguous timestamp row matching one value row."""
    exact_identity = _identity(value_row)
    if exact_identity in exact:
        return exact[exact_identity]

    base_identity = _identity(value_row, include_metric_name=False)
    candidates = without_name.get(base_identity, [])
    return candidates[0] if len(candidates) == 1 else None


def _paired_samples(value_row, timestamp_row, start, end):
    """Pair values with original sample timestamps and remove lookback copies."""
    values = dict(_matrix_samples(value_row))
    unique = {}
    for evaluation_time, original_timestamp in _matrix_samples(timestamp_row):
        if not start <= original_timestamp <= end:
            continue
        if evaluation_time not in values:
            continue
        unique[original_timestamp] = values[evaluation_time]
    return [
        {"timestamp": timestamp, "value": value}
        for timestamp, value in sorted(unique.items())
    ]


def _sample_result(sample):
    """Return one structured metric sample with UTC timestamp text."""
    return {
        "timestamp": sample["timestamp"],
        "timestamp_utc": _utc_timestamp(sample["timestamp"]),
        "value": sample["value"],
        "labels": sample["labels"],
    }


def _collect_metric_results(value_rows, timestamp_rows, start, end):
    """Build earliest/latest summaries for every dynamic OME metric name."""
    exact, without_name = _timestamp_rows_by_identity(timestamp_rows)
    metrics = {}
    for row in value_rows:
        labels = _labels(row)
        metric = labels.get("__name__", "")
        if not metric:
            continue
        metric_data = metrics.setdefault(
            metric,
            {"series_count": 0, "paired_series_count": 0, "samples": []},
        )
        metric_data["series_count"] += 1
        timestamp_row = _matching_timestamp_row(row, exact, without_name)
        if timestamp_row is None:
            continue
        samples = _paired_samples(row, timestamp_row, start, end)
        if not samples:
            continue
        metric_data["paired_series_count"] += 1
        metric_data["samples"].extend(
            {**sample, "labels": labels} for sample in samples
        )

    results = []
    incomplete = []
    current_time = time.time()
    for metric in sorted(metrics):
        metric_data = metrics[metric]
        samples = metric_data["samples"]
        if not samples:
            incomplete.append(metric)
            continue
        earliest = min(
            samples,
            key=lambda sample: (
                sample["timestamp"],
                sorted(sample["labels"].items()),
            ),
        )
        latest = max(
            samples,
            key=lambda sample: (
                sample["timestamp"],
                sorted(sample["labels"].items()),
            ),
        )
        results.append({
            "metric": metric,
            "series_count": metric_data["series_count"],
            "paired_series_count": metric_data["paired_series_count"],
            "sample_count": len(samples),
            "earliest": _sample_result(earliest),
            "latest": {
                **_sample_result(latest),
                "age_seconds": max(0.0, current_time - latest["timestamp"]),
            },
        })
    return results, incomplete


def _metric_details(endpoint, topic, start, end, metric_results):
    """Render the centralized tick-mark detail output for one OME topic."""
    metric_lines = [
        OME_DETAIL_MSGS["metric_result_line"].format(
            metric=value["metric"],
            series_count=value["series_count"],
            earliest_display=_display_timestamp(
                value["earliest"]["timestamp"]
            ),
            earliest_value=value["earliest"]["value"],
            latest_display=_display_timestamp(value["latest"]["timestamp"]),
            latest_value=value["latest"]["value"],
            age=value["latest"]["age_seconds"],
        )
        for value in metric_results
    ]
    return OME_DETAIL_MSGS["metrics_ready"].format(
        topic=topic,
        vmselect_ip=endpoint["ip"],
        vmselect_port=endpoint["port"],
        metric_count=len(metric_results),
        window_seconds=OME_VM_RANGE_WINDOW_SECONDS,
        start_display=_display_timestamp(start),
        end_display=_display_timestamp(end),
        metric_results="\n".join(metric_lines),
    )


def _verify_metric_topic_once(host, topic, identifier):
    """Query and summarize every OME metric in one source topic."""
    vmselect_ip, vmselect_port = get_vmselect_endpoint(host)
    if not vmselect_ip or not vmselect_port:
        raise _OmeVictoriaError(OME_ERROR_MSGS["vm_endpoint_missing"])
    endpoint = {"ip": vmselect_ip, "port": vmselect_port}
    end = time.time()
    start = end - OME_VM_RANGE_WINDOW_SECONDS
    selector = (
        "{source_subsystem=\""
        f"{_promql_value(identifier)}\",source_topic=\""
        f"{_promql_value(topic)}\"}}"
    )
    value_rows = _query_range_rows(
        host,
        endpoint,
        topic,
        selector,
        start,
        end,
    )
    if not value_rows:
        raise _OmeVictoriaError(
            OME_ERROR_MSGS["vm_data_missing"].format(topic=topic)
        )
    timestamp_rows = _query_range_rows(
        host,
        endpoint,
        topic,
        OME_TIMESTAMP_QUERY_TEMPLATE.format(selector=selector),
        start,
        end,
    )
    metric_results, incomplete = _collect_metric_results(
        value_rows,
        timestamp_rows,
        start,
        end,
    )
    if incomplete:
        raise _OmeVictoriaError(
            OME_ERROR_MSGS["vm_data_missing"].format(topic=topic)
        )
    if not metric_results:
        raise _OmeVictoriaError(
            OME_ERROR_MSGS["vm_data_missing"].format(topic=topic)
        )
    return _result(
        True,
        details=_metric_details(
            endpoint,
            topic,
            start,
            end,
            metric_results,
        ),
        topic=topic,
        source_subsystem=identifier,
        selector=selector,
        vmselect_ip=endpoint["ip"],
        vmselect_port=endpoint["port"],
        window={
            "start": start,
            "end": end,
            "seconds": OME_VM_RANGE_WINDOW_SECONDS,
        },
        metric_count=len(metric_results),
        metrics=[value["metric"] for value in metric_results],
        metric_results=metric_results,
    )


def _parse_log_timestamp(value):
    """Return an epoch value for a VictoriaLogs timestamp, when valid."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        timestamp = float(value)
        while timestamp > 100_000_000_000:
            timestamp /= 1000.0
        return timestamp if math.isfinite(timestamp) and timestamp > 0 else None
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _query_log_entries(host, endpoint, topic, identifier):
    """Return validated, exactly attributed VictoriaLogs entries."""
    query = (
        f'_msg_source:="{_logsql_value(identifier)}" AND '
        f'_msg_topic:="{_logsql_value(topic)}"'
    )
    command = OME_CMD_TEMPLATES["vl_query_topic"].format(
        vlselect_ip=endpoint["ip"],
        vlselect_port=endpoint["port"],
        query=urllib.parse.quote(query, safe=""),
        limit=OME_VL_QUERY_LIMIT,
        range=OME_VL_RANGE,
        timeout=OME_VICTORIA_QUERY_TIMEOUT_SECONDS,
    )
    command_result = run_on_kube_vip(host, command)
    if command_result.rc != 0:
        raise _OmeVictoriaError(
            OME_ERROR_MSGS["vl_query_failed"].format(topic=topic)
        )
    if not command_result.stdout.strip():
        return query, []

    entries = []
    for line in command_result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise _OmeVictoriaError(
                OME_ERROR_MSGS["vl_record_invalid"]
            ) from exc
        if not isinstance(entry, dict):
            raise _OmeVictoriaError(
                OME_ERROR_MSGS["vl_record_invalid"]
            )
        if (
            entry.get("_msg_source") == identifier
            and entry.get("_msg_topic") == topic
        ):
            entries.append(entry)
    return query, entries


def _display_log_value(value):
    """Return one compact, bounded field value for report output."""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, separators=(",", ":"), sort_keys=True)
    elif value is None:
        text = "null"
    elif isinstance(value, bool):
        text = str(value).lower()
    else:
        text = str(value)
    normalized = " ".join(text.split())
    if len(normalized) <= OME_VL_FIELD_VALUE_PREVIEW_LENGTH:
        return normalized
    return f"{normalized[:OME_VL_FIELD_VALUE_PREVIEW_LENGTH - 3]}..."


def _extract_log_fields(entry, topic):
    """Extract selected key/value fields from the latest OME Data record."""
    raw_message = entry.get("_msg")
    try:
        payload = json.loads(raw_message) if isinstance(raw_message, str) else {}
    except json.JSONDecodeError:
        payload = {}

    data = payload.get("Data") if isinstance(payload, dict) else None
    record = data[0] if isinstance(data, list) and data else None
    if not isinstance(record, dict):
        return []

    suffix = topic.rsplit(".", maxsplit=1)[-1]
    field_names = OME_VL_DISPLAY_FIELDS.get(suffix, ())
    return [
        {"key": key, "value": _display_log_value(record[key])}
        for key in field_names
        if key in record
    ]


def _log_details(endpoint, topic, log_result):
    """Render centralized tick-mark output for one OME log topic."""
    field_lines = [
        OME_DETAIL_MSGS["log_field_line"].format(**field)
        for field in log_result["latest"]["fields"]
    ]
    if not field_lines:
        field_lines.append(OME_DETAIL_MSGS["log_fields_unavailable"])
    result_line = OME_DETAIL_MSGS["log_result_line"].format(
        topic=topic,
        log_count=log_result["count"],
        earliest_display=_display_timestamp(
            log_result["earliest"]["timestamp"]
        ),
        latest_display=_display_timestamp(log_result["latest"]["timestamp"]),
        age=log_result["latest"]["age_seconds"],
        field_results="\n".join(field_lines),
    )
    return OME_DETAIL_MSGS["logs_ready"].format(
        topic=topic,
        vlselect_ip=endpoint["ip"],
        vlselect_port=endpoint["port"],
        window=OME_VL_RANGE,
        log_count=log_result["count"],
        log_result=result_line,
    )


def _verify_log_topic_once(host, topic, identifier):
    """Query and summarize exactly attributed OME logs for one topic."""
    vlselect_ip, vlselect_port = get_vlselect_endpoint(host)
    if not vlselect_ip or not vlselect_port:
        raise _OmeVictoriaError(OME_ERROR_MSGS["vl_endpoint_missing"])
    endpoint = {"ip": vlselect_ip, "port": vlselect_port}
    query, entries = _query_log_entries(host, endpoint, topic, identifier)
    if not entries:
        raise _OmeVictoriaError(
            OME_ERROR_MSGS["vl_data_missing"].format(topic=topic)
        )

    timestamped = []
    for entry in entries:
        timestamp = _parse_log_timestamp(entry.get("_time"))
        if timestamp is not None:
            timestamped.append({"timestamp": timestamp, "entry": entry})
    if not timestamped:
        raise _OmeVictoriaError(
            OME_ERROR_MSGS["vl_data_missing"].format(topic=topic)
        )

    earliest = min(timestamped, key=lambda value: value["timestamp"])
    latest = max(timestamped, key=lambda value: value["timestamp"])
    current_time = time.time()
    log_result = {
        "topic": topic,
        "count": len(entries),
        "earliest": {
            "timestamp": earliest["timestamp"],
            "timestamp_utc": _utc_timestamp(earliest["timestamp"]),
        },
        "latest": {
            "timestamp": latest["timestamp"],
            "timestamp_utc": _utc_timestamp(latest["timestamp"]),
            "age_seconds": max(0.0, current_time - latest["timestamp"]),
            "fields": _extract_log_fields(latest["entry"], topic),
        },
    }
    return _result(
        True,
        details=_log_details(endpoint, topic, log_result),
        topic=topic,
        source_subsystem=identifier,
        query=query,
        vlselect_ip=endpoint["ip"],
        vlselect_port=endpoint["port"],
        range=OME_VL_RANGE,
        log_count=log_result["count"],
        log_result=log_result,
    )


def _poll(verification, host, topic, identifier):
    """Poll one Victoria verification until success or its bounded timeout."""
    deadline = time.monotonic() + max(
        0,
        OME_VICTORIA_POLL_TIMEOUT_SECONDS,
    )
    last_error = None
    while True:
        try:
            return verification(host, topic, identifier)
        except _OmeVictoriaError as exc:
            last_error = exc

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(OME_VICTORIA_POLL_INTERVAL_SECONDS, remaining))
    raise last_error


def verify_ome_metrics_in_victoria(host, topic):
    """Verify every dynamic metric from one OME topic in VictoriaMetrics."""
    if topic not in OME_VICTORIA_METRIC_TOPICS:
        return _result(
            False,
            error=OME_ERROR_MSGS["topic_invalid"].format(
                data_type="metric",
                topic=topic,
            ),
        )
    try:
        context = _pipeline_context(host, "metrics")
        resolved_topic = _resolved_topic(topic, context["identifier"])
        if not context["source_enabled"] or not context["bridge_enabled"]:
            return _disabled_result("metrics", resolved_topic, context)
        result = _poll(
            _verify_metric_topic_once,
            host,
            resolved_topic,
            context["identifier"],
        )
        result["requested_topic"] = topic
        return result
    except (OSError, ValueError, _OmeVictoriaError) as exc:
        return _result(False, error=str(exc), topic=topic)


def verify_ome_logs_in_victoria(host, topic):
    """Verify exactly attributed entries from one OME topic in VictoriaLogs."""
    if topic not in OME_VICTORIA_LOG_TOPICS:
        return _result(
            False,
            error=OME_ERROR_MSGS["topic_invalid"].format(
                data_type="log",
                topic=topic,
            ),
        )
    try:
        context = _pipeline_context(host, "logs")
        resolved_topic = _resolved_topic(topic, context["identifier"])
        if not context["source_enabled"] or not context["bridge_enabled"]:
            return _disabled_result("logs", resolved_topic, context)
        result = _poll(
            _verify_log_topic_once,
            host,
            resolved_topic,
            context["identifier"],
        )
        result["requested_topic"] = topic
        return result
    except (OSError, ValueError, _OmeVictoriaError) as exc:
        return _result(False, error=str(exc), topic=topic)
