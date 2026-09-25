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

"""Unit tests for source- and bridge-derived telemetry sink enablement."""

import pytest

from library.functions import telemetry_func


SINKS = {"kafka", "victoria_metrics", "victoria_logs"}


def _enabled_sinks(monkeypatch, config):
    """Return sinks considered enabled for a supplied telemetry config."""
    monkeypatch.setattr(
        telemetry_func,
        "load_telemetry_config_from_target",
        lambda _host: config,
    )
    return {
        sink for sink in SINKS
        if telemetry_func.is_sink_enabled(object(), sink)
    }


def test_sink_enablement_keeps_direct_source_targets(monkeypatch):
    """Keep enabled source collection targets as direct sink requirements."""
    config = {
        "telemetry_sources": {
            "idrac": {
                "metrics_enabled": True,
                "logs_enabled": False,
                "collection_targets": ["kafka", "victoria_metrics"],
            },
            "powerscale": {
                "metrics_enabled": False,
                "logs_enabled": False,
                "collection_targets": ["victoria_logs"],
            },
        },
        "telemetry_bridges": {},
    }

    assert _enabled_sinks(monkeypatch, config) == {
        "kafka",
        "victoria_metrics",
    }


@pytest.mark.parametrize(
    ("metrics_enabled", "logs_enabled", "expected"),
    [
        (True, False, {"kafka", "victoria_metrics"}),
        (False, True, {"kafka", "victoria_logs"}),
        (True, True, {"kafka", "victoria_metrics", "victoria_logs"}),
        (False, False, {"kafka"}),
    ],
)
def test_vector_ome_bridge_derives_required_sinks(
        monkeypatch, metrics_enabled, logs_enabled, expected):
    """Derive Kafka and Victoria sinks from Vector-OME bridge flags."""
    config = {
        "telemetry_sources": {
            "ome": {
                "metrics_enabled": True,
                "logs_enabled": True,
                "collection_targets": ["kafka"],
            },
        },
        "telemetry_bridges": {
            "vector_ome": {
                "metrics_enabled": metrics_enabled,
                "logs_enabled": logs_enabled,
            },
        },
    }

    assert _enabled_sinks(monkeypatch, config) == expected


@pytest.mark.parametrize(
    ("source_enabled", "bridge_enabled", "expected"),
    [
        (True, True, {"kafka", "victoria_metrics"}),
        (True, False, set()),
        (False, True, set()),
    ],
)
def test_vector_ldms_bridge_requires_enabled_ldms_source(
        monkeypatch, source_enabled, bridge_enabled, expected):
    """Mirror the playbook gate for Vector-LDMS sink requirements."""
    config = {
        "telemetry_sources": {
            "ldms": {
                "metrics_enabled": source_enabled,
                "logs_enabled": False,
                "collection_targets": [],
            },
        },
        "telemetry_bridges": {
            "vector_ldms": {"metrics_enabled": bridge_enabled},
        },
    }

    assert _enabled_sinks(monkeypatch, config) == expected
