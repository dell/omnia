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

"""Unit tests for OME Kafka endpoint and polling behavior."""

import json
from types import SimpleNamespace

import pytest

from library.functions import ome_func
from library.vars import (
    KAFKA_BRIDGE_SERVICE,
    KAFKA_EXTERNAL_BOOTSTRAP_SVC,
    OME_KAFKA_CONNECTION_POLL_INTERVAL_SECONDS,
    OME_KAFKA_CONNECTION_TIMEOUT_SECONDS,
    OME_KAFKA_DATA_POLL_INTERVAL_SECONDS,
    OME_KAFKA_DATA_TIMEOUT_SECONDS,
    OME_KAFKA_TOPIC_POLL_INTERVAL_SECONDS,
    OME_KAFKA_TOPIC_TIMEOUT_SECONDS,
    OME_KAFKA_TOPICS,
    OME_TEST_KAFKA_BOOTSTRAP,
    OME_TEST_KAFKA_BRIDGE_BOOTSTRAP,
    OME_TEST_KAFKA_BRIDGE_ENDPOINT,
    OME_TEST_KAFKA_BRIDGE_HOST,
)


class _FakeClock:
    """Deterministic monotonic clock for retry tests."""

    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        """Return the current simulated time."""
        return self.now

    def sleep(self, seconds):
        """Advance simulated time instead of blocking the test."""
        self.now += seconds


def _connectivity_result(success, status):
    """Build a minimal OME connectivity result."""
    return {
        "success": success,
        "status": status,
        "error": "" if success else f"Kafka status: {status}",
    }


def test_ome_polling_timeouts():
    """Use five minutes for connection and two minutes for topic data."""
    assert OME_KAFKA_CONNECTION_TIMEOUT_SECONDS == 300
    assert OME_KAFKA_CONNECTION_POLL_INTERVAL_SECONDS == 10
    assert OME_KAFKA_TOPIC_TIMEOUT_SECONDS == 120
    assert OME_KAFKA_TOPIC_POLL_INTERVAL_SECONDS == 2
    assert OME_KAFKA_DATA_TIMEOUT_SECONDS == 120
    assert OME_KAFKA_DATA_POLL_INTERVAL_SECONDS == 2


@pytest.mark.parametrize(
    (
        "source_metrics",
        "source_logs",
        "bridge_metrics",
        "bridge_logs",
        "expected_topics",
    ),
    [
        (
            True,
            False,
            True,
            False,
            ["rack_ome.telemetry", "rack_ome.inventory", "rack_ome.health"],
        ),
        (
            False,
            True,
            False,
            True,
            ["rack_ome.alerts", "rack_ome.auditlogs"],
        ),
        (
            True,
            True,
            True,
            True,
            [
                "rack_ome.telemetry",
                "rack_ome.inventory",
                "rack_ome.alerts",
                "rack_ome.health",
                "rack_ome.auditlogs",
            ],
        ),
        (False, False, False, False, []),
    ],
)
def test_ome_pipeline_context_selects_source_topics(
        monkeypatch, source_metrics, source_logs, bridge_metrics, bridge_logs,
        expected_topics):
    """Select only enabled source topics and apply the deployed identifier."""
    monkeypatch.setattr(
        ome_func,
        "load_telemetry_config_from_target",
        lambda _host: {
            "telemetry_sources": {
                "ome": {
                    "metrics_enabled": source_metrics,
                    "logs_enabled": source_logs,
                },
            },
            "telemetry_bridges": {
                "vector_ome": {
                    "metrics_enabled": bridge_metrics,
                    "logs_enabled": bridge_logs,
                    "ome_identifier": "rack_ome",
                },
            },
        },
    )

    context = ome_func.get_ome_pipeline_context(object())

    assert context["config_valid"] is True
    assert context["source_metrics_enabled"] is source_metrics
    assert context["source_logs_enabled"] is source_logs
    assert context["bridge_metrics_enabled"] is bridge_metrics
    assert context["bridge_logs_enabled"] is bridge_logs
    assert context["metrics_pipeline_enabled"] is (
        source_metrics and bridge_metrics
    )
    assert context["logs_pipeline_enabled"] is (
        source_logs and bridge_logs
    )
    assert context["expected_topics"] == expected_topics


def test_configure_ome_reconciles_connected_stale_broker(monkeypatch):
    """Force TestConnection and Save before accepting Connected."""
    statuses = iter([
        _connectivity_result(True, "Connected"),
        _connectivity_result(True, "Connected"),
    ])
    action_calls = []

    monkeypatch.setattr(
        ome_func, "verify_ome_kafka_connectivity", lambda *args: next(statuses)
    )

    def _action_result(*args):
        action_calls.append(args)
        return {"success": True, "http_code": 200, "error": ""}

    monkeypatch.setattr(
        ome_func, "send_ome_kafka_test_connection", _action_result,
    )
    monkeypatch.setattr(
        ome_func, "update_ome_forwarder_settings", _action_result,
    )
    monkeypatch.setattr(ome_func.time, "sleep", lambda _seconds: None)

    result = ome_func.configure_ome_kafka_and_wait(
        object(), "ome.example", "admin", "secret", "kafka.example:9094",
        force_configuration=True,
    )

    assert result["success"] is True
    assert result["attempts"] == 2
    assert result["test_connection_attempts"] == 1
    assert result["settings_update_attempts"] == 1
    assert len(action_calls) == 2


def test_configure_ome_retries_transient_test_connection(monkeypatch):
    """Retry TestConnection before saving and accepting Connected."""
    statuses = iter([
        _connectivity_result(False, "Disconnected"),
        _connectivity_result(False, "Disconnected"),
        _connectivity_result(True, "Connected"),
    ])
    test_results = iter([
        {"success": False, "http_code": 400, "error": "HTTP 400"},
        {"success": True, "http_code": 200, "error": ""},
    ])
    save_result = {"success": True, "http_code": 200, "error": ""}

    monkeypatch.setattr(
        ome_func, "verify_ome_kafka_connectivity", lambda *args: next(statuses)
    )
    monkeypatch.setattr(
        ome_func, "send_ome_kafka_test_connection",
        lambda *args: next(test_results),
    )
    monkeypatch.setattr(
        ome_func, "update_ome_forwarder_settings", lambda *args: save_result
    )
    monkeypatch.setattr(ome_func.time, "sleep", lambda _seconds: None)

    result = ome_func.configure_ome_kafka_and_wait(
        object(), "ome.example", "admin", "secret", "kafka.example:9094"
    )

    assert result["success"] is True
    assert result["attempts"] == 3
    assert result["test_connection_attempts"] == 2
    assert result["settings_update_attempts"] == 1


def test_configure_ome_accepts_spontaneous_reconnection(monkeypatch):
    """Accept authoritative Connected when a matching broker recovers itself."""
    statuses = iter([
        _connectivity_result(False, "Disconnected"),
        _connectivity_result(True, "Connected"),
    ])
    monkeypatch.setattr(
        ome_func, "verify_ome_kafka_connectivity", lambda *args: next(statuses)
    )
    monkeypatch.setattr(
        ome_func,
        "send_ome_kafka_test_connection",
        lambda *args: {"success": False, "http_code": 409, "error": "busy"},
    )
    monkeypatch.setattr(ome_func.time, "sleep", lambda _seconds: None)

    result = ome_func.configure_ome_kafka_and_wait(
        object(), "ome.example", "admin", "secret", "kafka.example:9094",
    )

    assert result["success"] is True
    assert result["attempts"] == 2
    assert result["test_connection_attempts"] == 1
    assert result["settings_update_attempts"] == 0


def test_configure_ome_stops_on_authentication_error(monkeypatch):
    """Do not retry configuration when OME rejects authentication."""
    monkeypatch.setattr(
        ome_func,
        "verify_ome_kafka_connectivity",
        lambda *args: _connectivity_result(False, "AuthError"),
    )

    result = ome_func.configure_ome_kafka_and_wait(
        object(), "ome.example", "admin", "bad", "kafka.example:9094"
    )

    assert result["success"] is False
    assert result["attempts"] == 1
    assert result["test_connection_attempts"] == 0
    assert result["settings_update_attempts"] == 0


def test_configure_ome_stops_on_action_http_403(monkeypatch):
    """Do not spend five minutes retrying an unauthorized POST action."""
    monkeypatch.setattr(
        ome_func,
        "verify_ome_kafka_connectivity",
        lambda *args: _connectivity_result(False, "Disconnected"),
    )
    monkeypatch.setattr(
        ome_func,
        "send_ome_kafka_test_connection",
        lambda *args: {"success": False, "http_code": 403, "error": "HTTP 403"},
    )

    result = ome_func.configure_ome_kafka_and_wait(
        object(), "ome.example", "viewer", "secret", "kafka.example:9094"
    )

    assert result["success"] is False
    assert result["status"] == "AuthError"
    assert result["test_connection_attempts"] == 1
    assert result["settings_update_attempts"] == 0


def test_configure_ome_stops_at_polling_timeout(monkeypatch):
    """Stop connection retries at the configured monotonic polling deadline."""
    clock = _FakeClock()
    monkeypatch.setattr(
        ome_func,
        "verify_ome_kafka_connectivity",
        lambda *args: _connectivity_result(False, "Disconnected"),
    )
    monkeypatch.setattr(
        ome_func,
        "send_ome_kafka_test_connection",
        lambda *args: {"success": False, "http_code": 409, "error": "HTTP 409"},
    )
    monkeypatch.setattr(ome_func.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(ome_func.time, "sleep", clock.sleep)

    result = ome_func.configure_ome_kafka_and_wait(
        object(), "ome.example", "admin", "secret", "kafka.example:9094",
        timeout_seconds=20, poll_interval_seconds=10,
    )

    assert result["success"] is False
    assert result["timed_out"] is True
    assert result["attempts"] == 3
    assert result["elapsed_seconds"] == 20.0


def test_configure_ome_retries_transient_save_failure(monkeypatch):
    """Retry Save without repeating an accepted TestConnection action."""
    clock = _FakeClock()
    statuses = iter([
        _connectivity_result(False, "Disconnected"),
        _connectivity_result(False, "Disconnected"),
        _connectivity_result(True, "Connected"),
    ])
    save_results = iter([
        {"success": False, "http_code": 409, "error": "HTTP 409"},
        {"success": True, "http_code": 200, "error": ""},
    ])

    monkeypatch.setattr(
        ome_func, "verify_ome_kafka_connectivity", lambda *args: next(statuses)
    )
    monkeypatch.setattr(
        ome_func, "send_ome_kafka_test_connection",
        lambda *args: {"success": True, "http_code": 200, "error": ""},
    )
    monkeypatch.setattr(
        ome_func, "update_ome_forwarder_settings",
        lambda *args: next(save_results),
    )
    monkeypatch.setattr(ome_func.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(ome_func.time, "sleep", clock.sleep)

    result = ome_func.configure_ome_kafka_and_wait(
        object(), "ome.example", "admin", "secret", "kafka.example:9094"
    )

    assert result["success"] is True
    assert result["test_connection_attempts"] == 1
    assert result["settings_update_attempts"] == 2
    assert result["elapsed_seconds"] == 20.0


def test_ome_forwarder_actions_require_documented_http_200(monkeypatch):
    """Accept the documented OME action response and reject other codes."""
    args = (
        object(), "ome.example", "admin", "secret", "kafka.example:9094",
    )

    calls = []
    response = SimpleNamespace(rc=0, stdout="HTTP_CODE:200", stderr="")

    def _run_action(_host, command, *args):
        calls.append((command, args))
        return response

    monkeypatch.setattr(ome_func, "run_on_host", _run_action)
    test_result = ome_func.send_ome_kafka_test_connection(*args)
    save_result = ome_func.update_ome_forwarder_settings(*args)
    assert test_result["success"] is True
    assert save_result["success"] is True
    assert "Actions/DataForwardingService.TestConnection" in calls[0][1][-1]
    assert "Actions/DataForwardingService.ForwarderSettings" in calls[1][1][-1]
    test_payload = json.loads(calls[0][1][1])
    save_payload = json.loads(calls[1][1][1])
    assert test_payload["Id"] == 10
    assert test_payload["ForwarderConfigurations"]
    assert save_payload["Enabled"] is True

    response = SimpleNamespace(rc=0, stdout="HTTP_CODE:202", stderr="")
    monkeypatch.setattr(ome_func, "run_on_host", lambda *_args: response)
    assert ome_func.send_ome_kafka_test_connection(*args)["success"] is False
    assert ome_func.update_ome_forwarder_settings(*args)["success"] is False

    response = SimpleNamespace(
        rc=0,
        stdout=(
            '{"error":{"message":"Broker certificate is not trusted"}}'
            "\nHTTP_CODE:400"
        ),
        stderr="",
    )
    monkeypatch.setattr(ome_func, "run_on_host", lambda *_args: response)
    result = ome_func.send_ome_kafka_test_connection(*args)
    assert result["error"] == "HTTP 400: Broker certificate is not trusted"


def test_ome_api_values_use_testinfra_quoted_arguments(monkeypatch):
    """Keep hostile OME credentials and payload values out of shell templates."""
    captured = {}
    response = SimpleNamespace(
        rc=0, stdout=json.dumps({"value": []}), stderr="",
    )

    def _run_action(_host, command, *args):
        captured.update(command=command, args=args)
        return response

    monkeypatch.setattr(ome_func, "run_on_host", _run_action)
    ome_user = "admin'; touch /tmp/must-not-run; '"
    ome_secret = "secret $(must-not-run)"

    result = ome_func.get_ome_forwarders(
        object(), "ome.example", ome_user, ome_secret,
    )

    assert result["success"] is True
    assert ome_user not in captured["command"]
    assert ome_secret not in captured["command"]
    assert captured["command"].count("%s") == 2
    assert captured["args"] == (
        f"{ome_user}:{ome_secret}",
        "https://ome.example/api/DataForwardingService/Forwarders",
    )


def test_ome_pfx_secret_uses_testinfra_quoted_argument(monkeypatch):
    """Keep a hostile PFX passphrase out of the OpenSSL shell template."""
    calls = []
    responses = iter([
        SimpleNamespace(rc=0, stdout="", stderr=""),
        SimpleNamespace(rc=0, stdout="exists\n", stderr=""),
    ])

    def _run_action(_host, command, *args):
        calls.append((command, args))
        return next(responses)

    monkeypatch.setattr(ome_func, "run_on_host", _run_action)
    monkeypatch.setattr(
        ome_func, "_get_cert_dir", lambda _host: "/private/cert path",
    )
    pfx_secret = "secret'; touch /tmp/must-not-run; '"

    result = ome_func.convert_certs_to_pfx(object(), pfx_secret)

    assert result["success"] is True
    assert pfx_secret not in calls[0][0]
    assert calls[0][0].count("%s") == 4
    assert calls[0][1] == (
        "/private/cert path/user.pfx",
        "/private/cert path/user.key",
        "/private/cert path/user.crt",
        f"pass:{pfx_secret}",
    )
    assert calls[1][1] == ("/private/cert path/user.pfx",)


def test_ome_connectivity_stops_on_empty_http_401(monkeypatch):
    """Classify an empty HTTP 401 response without entering the retry window."""
    response = SimpleNamespace(rc=0, stdout="\nHTTP_CODE:401", stderr="")
    monkeypatch.setattr(ome_func, "run_on_host", lambda *_args: response)

    result = ome_func.verify_ome_kafka_connectivity(
        object(), "ome.example", "admin", "bad-secret",
    )

    assert result["success"] is False
    assert result["status"] == "AuthError"


def test_ome_connectivity_recognizes_body_permission_error(monkeypatch):
    """Classify OME insufficient-privilege response as authentication failure."""
    body = json.dumps({"error": {"message": "Insufficient privilege"}})
    response = SimpleNamespace(
        rc=0, stdout=f"{body}\nHTTP_CODE:200", stderr="",
    )
    monkeypatch.setattr(ome_func, "run_on_host", lambda *_args: response)

    result = ome_func.verify_ome_kafka_connectivity(
        object(), "ome.example", "viewer", "secret",
    )

    assert result["success"] is False
    assert result["status"] == "AuthError"


def test_get_ome_forwarder_config_reads_saved_broker(monkeypatch):
    """Read BrokerList from the OME forwarder configuration collection."""
    body = json.dumps({
        "value": [
            {
                "ConfigurationName": "BrokerList",
                "ConfigurationValue": OME_TEST_KAFKA_BOOTSTRAP,
            },
            {
                "ConfigurationName": "AuthMode",
                "ConfigurationValue": "2",
            },
        ],
    })
    response = SimpleNamespace(
        rc=0, stdout=f"{body}\nHTTP_CODE:200", stderr="",
    )
    monkeypatch.setattr(ome_func, "run_on_host", lambda *_args: response)

    result = ome_func.get_ome_kafka_forwarder_config(
        object(), "ome.example", "admin", "secret",
    )

    assert result["success"] is True
    assert result["broker_list"] == OME_TEST_KAFKA_BOOTSTRAP


def test_external_kafka_details_reject_http_bridge_as_bootstrap(monkeypatch):
    """Reject the old export that mislabeled HTTP Bridge as bootstrap."""
    monkeypatch.setattr(ome_func, "_get_cert_dir", lambda _host: "/output")
    monkeypatch.setattr(
        ome_func,
        "read_remote_yaml",
        lambda *_args: {
            "kafka": {
                "loadbalancer_service": KAFKA_BRIDGE_SERVICE,
                "bootstrap_server": OME_TEST_KAFKA_BRIDGE_BOOTSTRAP,
            }
        },
    )
    monkeypatch.setattr(
        ome_func, "get_kafka_external_bootstrap", lambda _host: OME_TEST_KAFKA_BOOTSTRAP
    )
    monkeypatch.setattr(
        ome_func, "get_kafka_bridge_ip", lambda _host: OME_TEST_KAFKA_BRIDGE_HOST
    )
    monkeypatch.setattr(ome_func, "get_kafka_bridge_port", lambda _host: "8080")

    result = ome_func.verify_external_kafka_connection_details(object())

    assert result["success"] is False
    assert "bootstrap_server" in result["error"]


def test_external_kafka_details_accept_distinct_native_and_rest_endpoints(
        monkeypatch):
    """Accept a native OME bootstrap plus a separate HTTP Bridge endpoint."""
    monkeypatch.setattr(ome_func, "_get_cert_dir", lambda _host: "/output")
    monkeypatch.setattr(
        ome_func,
        "read_remote_yaml",
        lambda *_args: {
            "kafka": {
                "loadbalancer_service": KAFKA_EXTERNAL_BOOTSTRAP_SVC,
                "bootstrap_server": OME_TEST_KAFKA_BOOTSTRAP,
                "bridge": {
                    "loadbalancer_service": KAFKA_BRIDGE_SERVICE,
                    "endpoint": OME_TEST_KAFKA_BRIDGE_ENDPOINT,
                },
            }
        },
    )
    monkeypatch.setattr(
        ome_func, "get_kafka_external_bootstrap", lambda _host: OME_TEST_KAFKA_BOOTSTRAP
    )
    monkeypatch.setattr(
        ome_func, "get_kafka_bridge_ip", lambda _host: OME_TEST_KAFKA_BRIDGE_HOST
    )
    monkeypatch.setattr(ome_func, "get_kafka_bridge_port", lambda _host: "8080")

    result = ome_func.verify_external_kafka_connection_details(object())

    assert result["success"] is True
    assert not result["mismatches"]


def test_ome_topics_retry_until_all_topics_exist(monkeypatch):
    """Retry topic enumeration while OME creates topics asynchronously."""
    responses = iter([
        SimpleNamespace(rc=0, stdout='["ome.telemetry"]', stderr=""),
        SimpleNamespace(rc=0, stdout=json.dumps(OME_KAFKA_TOPICS), stderr=""),
    ])
    monkeypatch.setattr(
        ome_func, "get_kafka_bridge_ip", lambda _host: OME_TEST_KAFKA_BRIDGE_HOST
    )
    monkeypatch.setattr(ome_func, "get_kafka_bridge_port", lambda _host: "8080")
    monkeypatch.setattr(
        ome_func, "run_on_kube_vip", lambda *_args: next(responses)
    )
    monkeypatch.setattr(ome_func.time, "sleep", lambda _seconds: None)

    result = ome_func.verify_ome_kafka_topics(object())

    assert result["success"] is True
    assert result["attempts"] == 2
    assert result["missing_topics"] == []


def test_ome_topics_accepts_expected_subset(monkeypatch):
    """Ignore topic families disabled by the OME source configuration."""
    log_topics = ["ome.alerts", "ome.auditlogs"]
    monkeypatch.setattr(
        ome_func, "get_kafka_bridge_ip", lambda _host: OME_TEST_KAFKA_BRIDGE_HOST
    )
    monkeypatch.setattr(ome_func, "get_kafka_bridge_port", lambda _host: "8080")
    monkeypatch.setattr(
        ome_func,
        "run_on_kube_vip",
        lambda *_args: SimpleNamespace(
            rc=0,
            stdout=json.dumps(log_topics),
            stderr="",
        ),
    )

    result = ome_func.verify_ome_kafka_topics(
        object(),
        timeout_seconds=0,
        expected_topics=log_topics,
    )

    assert result["success"] is True
    assert result["found_topics"] == log_topics
    assert result["missing_topics"] == []
    assert result["all_topics"] == log_topics
    assert result["expected_topics"] == log_topics
    assert result["attempts"] == 1


def test_ome_data_retries_for_delayed_records(monkeypatch):
    """Poll a data topic until a delayed record arrives within two minutes."""
    clock = _FakeClock()
    record = {
        "partition": 0,
        "offset": 1,
        "timestamp": 1_700_000_000_000,
        "value": [{"Name": "server-01"}],
    }
    responses = iter([
        SimpleNamespace(rc=0, stdout='{"instance_id":"consumer"}', stderr=""),
        SimpleNamespace(rc=0, stdout="", stderr=""),
        SimpleNamespace(rc=0, stdout="[]", stderr=""),
        SimpleNamespace(rc=0, stdout=json.dumps([record]), stderr=""),
        SimpleNamespace(rc=0, stdout="", stderr=""),
    ])
    monkeypatch.setattr(
        ome_func, "get_kafka_bridge_ip", lambda _host: OME_TEST_KAFKA_BRIDGE_HOST
    )
    monkeypatch.setattr(ome_func, "get_kafka_bridge_port", lambda _host: "8080")
    monkeypatch.setattr(
        ome_func, "run_on_kube_vip", lambda *_args: next(responses)
    )
    monkeypatch.setattr(ome_func.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(ome_func.time, "sleep", clock.sleep)

    result = ome_func.verify_ome_data_in_kafka(
        object(), topic="ome.telemetry",
    )

    assert result["success"] is True
    assert result["records_found"] == 1
    assert result["attempts"] == 2
    assert result["elapsed_seconds"] == 2.0
