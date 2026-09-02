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

"""Unit tests for OME Victoria sink verification helpers."""

import json

from library.functions import ome_victoria_func


def _matrix_row(metric, values):
    """Build one VictoriaMetrics matrix row for a shared OME identity."""
    return {
        "metric": {
            "__name__": metric,
            "component": "SystemBoard",
            "identifier": "device-1",
            "source_subsystem": "ome",
            "source_topic": "ome.telemetry",
            "type": "Power",
        },
        "values": values,
    }


def test_collect_metric_results_uses_original_sample_timestamps(monkeypatch):
    """Pair values with timestamp() data instead of evaluation timestamps."""
    value_rows = [
        _matrix_row("power_watts", [[100, "12.5"], [160, "14.0"]]),
    ]
    timestamp_rows = [
        _matrix_row("power_watts", [[100, "90"], [160, "150"]]),
    ]
    monkeypatch.setattr(ome_victoria_func.time, "time", lambda: 200.0)

    results, incomplete = ome_victoria_func._collect_metric_results(
        value_rows,
        timestamp_rows,
        80,
        170,
    )

    assert incomplete == []
    assert len(results) == 1
    assert results[0]["earliest"]["timestamp"] == 90
    assert results[0]["earliest"]["value"] == 12.5
    assert results[0]["latest"]["timestamp"] == 150
    assert results[0]["latest"]["value"] == 14.0
    assert results[0]["latest"]["age_seconds"] == 50


def test_collect_metric_results_keeps_metrics_with_identical_labels():
    """Preserved metric names prevent timestamp rows from colliding."""
    value_rows = [
        _matrix_row("power_watts", [[100, "12.5"]]),
        _matrix_row("temperature_celsius", [[100, "38"]]),
    ]
    timestamp_rows = [
        _matrix_row("power_watts", [[100, "90"]]),
        _matrix_row("temperature_celsius", [[100, "95"]]),
    ]

    results, incomplete = ome_victoria_func._collect_metric_results(
        value_rows,
        timestamp_rows,
        80,
        110,
    )

    assert incomplete == []
    assert [result["metric"] for result in results] == [
        "power_watts",
        "temperature_celsius",
    ]


def test_verify_metrics_normalizes_custom_ome_identifier(monkeypatch):
    """Use the configured identifier for both subsystem and topic labels."""
    monkeypatch.setattr(
        ome_victoria_func,
        "_pipeline_context",
        lambda *_args: {
            "source_enabled": True,
            "bridge_enabled": True,
            "identifier": "rack_ome",
        },
    )
    captured = {}

    def _poll(_verification, _host, topic, identifier):
        captured.update(topic=topic, identifier=identifier)
        return {"success": True, "details": "ok", "error": ""}

    monkeypatch.setattr(ome_victoria_func, "_poll", _poll)

    result = ome_victoria_func.verify_ome_metrics_in_victoria(
        object(),
        "ome.telemetry",
    )

    assert result["success"] is True
    assert captured == {
        "topic": "rack_ome.telemetry",
        "identifier": "rack_ome",
    }


def test_verify_logs_skips_when_bridge_is_disabled(monkeypatch):
    """An intentionally disabled logs path is skipped rather than failed."""
    monkeypatch.setattr(
        ome_victoria_func,
        "_pipeline_context",
        lambda *_args: {
            "source_enabled": True,
            "bridge_enabled": False,
            "identifier": "ome",
        },
    )

    result = ome_victoria_func.verify_ome_logs_in_victoria(
        object(),
        "ome.alerts",
    )

    assert result["success"] is True
    assert result["skipped"] is True
    assert result["source_enabled"] is True
    assert result["bridge_enabled"] is False


def test_parse_log_timestamp_accepts_iso_and_nanoseconds():
    """Normalize the timestamp representations returned by VictoriaLogs."""
    iso_value = ome_victoria_func._parse_log_timestamp(
        "2026-09-02T11:22:01Z"
    )
    nanosecond_value = ome_victoria_func._parse_log_timestamp(
        1_788_348_121_000_000_000
    )

    assert iso_value == 1_788_348_121
    assert nanosecond_value == 1_788_348_121


def test_extract_log_fields_returns_readable_key_values():
    """Render selected OME fields instead of one dense JSON message."""
    entry = {
        "_msg": json.dumps({
            "Data": [{
                "AlertId": 5518,
                "AlertIdentifier": "DWZKTH4",
                "Description": "Unable to collect device metrics",
                "IsAcknowledged": False,
                "Severity": 8,
                "Timestamp": "20260902T113700Z",
                "Ignored": "not displayed",
            }],
        }),
    }

    fields = ome_victoria_func._extract_log_fields(entry, "ome.alerts")

    assert fields == [
        {"key": "AlertId", "value": "5518"},
        {"key": "AlertIdentifier", "value": "DWZKTH4"},
        {
            "key": "Description",
            "value": "Unable to collect device metrics",
        },
        {"key": "IsAcknowledged", "value": "false"},
        {"key": "Severity", "value": "8"},
        {"key": "Timestamp", "value": "20260902T113700Z"},
    ]
