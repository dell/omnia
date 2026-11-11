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

"""Unit tests for configured-disabled FVT Kubernetes checks."""

import json
from types import SimpleNamespace

from library.functions import k8s_func, powerscale_func, telemetry_func


def _result(stdout="", rc=0, stderr=""):
    return SimpleNamespace(stdout=stdout, rc=rc, stderr=stderr)


def test_retained_zero_replica_workload_is_stopped(monkeypatch):
    """A retained controller with no active replicas or pods must pass."""
    responses = iter([
        _result(json.dumps({
            "spec": {"replicas": 0},
            "status": {"readyReplicas": 0},
        })),
        _result(json.dumps({"items": []})),
    ])
    monkeypatch.setattr(
        k8s_func, "run_on_kube_vip", lambda *_args: next(responses),
    )

    result = k8s_func.verify_workloads_stopped(object(), [{
        "kind": "deployment",
        "name": "source-adapter",
        "selector": "app=source-adapter",
    }])

    assert result["success"] is True
    assert result["workloads"][0]["exists"] is True


def test_disabled_workload_fails_when_a_pod_remains(monkeypatch):
    """A terminating or orphaned source pod must fail the disabled-state FVT."""
    responses = iter([
        _result(""),
        _result(json.dumps({
            "items": [{"metadata": {"name": "source-adapter-old"}}],
        })),
    ])
    monkeypatch.setattr(
        k8s_func, "run_on_kube_vip", lambda *_args: next(responses),
    )

    result = k8s_func.verify_workloads_stopped(object(), [{
        "kind": "deployment",
        "name": "source-adapter",
        "selector": "app=source-adapter",
    }])

    assert result["success"] is False
    assert "source-adapter-old" in result["error"]


def test_shared_sink_check_only_requires_configured_sinks(monkeypatch):
    """Disabled sinks are informational while required shared sinks are checked."""
    monkeypatch.setattr(
        telemetry_func,
        "is_sink_enabled",
        lambda _host, sink: sink == "victoria_metrics",
    )

    def _pods(_host, prefix, namespace=None, min_count=1):
        del namespace, min_count
        pods = [{
            "name": f"{prefix}-0",
            "status": "Running",
            "running": True,
        }]
        if prefix == "vmagent":
            pods.insert(0, {
                "name": "vmagent-vector-0",
                "status": "Running",
                "running": True,
            })
        return {
            "success": True,
            "running_count": len(pods),
            "total_count": len(pods),
            "pods": pods,
        }

    monkeypatch.setattr(k8s_func, "verify_pods_by_prefix", _pods)

    result = k8s_func.verify_enabled_shared_sinks(object())

    assert result["success"] is True
    assert result["sinks"]["victoria_metrics"]["checked"] is True
    assert result["sinks"]["kafka"]["checked"] is False
    agent_pods = result["sinks"]["victoria_metrics"]["components"][
        "vmagent"
    ]["pods"]
    assert [pod["name"] for pod in agent_pods] == ["vmagent-0"]


def test_shared_sink_check_rejects_vector_agent_as_shared_agent(monkeypatch):
    """vmagent-vector alone must not satisfy the shared vmagent requirement."""
    monkeypatch.setattr(
        telemetry_func,
        "is_sink_enabled",
        lambda _host, sink: sink == "victoria_metrics",
    )

    def _pods(_host, prefix, namespace=None, min_count=1):
        del namespace, min_count
        name = "vmagent-vector-0" if prefix == "vmagent" else f"{prefix}-0"
        return {
            "success": True,
            "running_count": 1,
            "total_count": 1,
            "pods": [{"name": name, "status": "Running", "running": True}],
        }

    monkeypatch.setattr(k8s_func, "verify_pods_by_prefix", _pods)

    result = k8s_func.verify_enabled_shared_sinks(object())

    assert result["success"] is False
    assert result["sinks"]["victoria_metrics"]["components"][
        "vmagent"
    ]["success"] is False


def test_powerscale_quiet_window_counts_only_returned_samples(monkeypatch):
    """PowerScale VM quiet-window queries count each returned timestamp."""
    monkeypatch.setattr(
        powerscale_func,
        "get_vmselect_endpoint",
        lambda _host: ("vmselect", "8481"),
    )
    output = "\n".join([
        json.dumps({
            "metric": {"__name__": "karavi_topology_metrics"},
            "timestamps": [10, 11],
        }),
        json.dumps({
            "metric": {"__name__": "powerscale_volume_count"},
            "timestamps": [12],
        }),
    ])
    monkeypatch.setattr(
        powerscale_func,
        "run_on_kube_vip",
        lambda *_args: _result(output),
    )

    result = powerscale_func.query_powerscale_vm_samples(
        object(), 10, 20,
    )

    assert result["success"] is True
    assert result["sample_count"] == 3
    assert result["metric_counts"]["karavi_topology_metrics"] == 2


def test_powerscale_test_event_uses_unique_marker(monkeypatch):
    """The OneFS test-event trigger carries the run-specific marker."""
    captured = {}

    def _run(_host, target, user, command):
        captured.update(target=target, user=user, command=command)
        return _result("created")

    monkeypatch.setattr(powerscale_func, "run_ssh_command", _run)
    marker = "powerscale-fvt-disabled-abc123"
    result = powerscale_func.trigger_powerscale_test_event(
        object(),
        {
            "endpoint": "https://powerscale.example",
            "username": "telemetry",
            "password": "unused",
        },
        marker,
    )

    assert result["success"] is True
    assert captured == {
        "target": "powerscale.example",
        "user": "telemetry",
        "command": f"isi event test create {marker}",
    }


def test_powerscale_log_query_matches_only_marker(monkeypatch):
    """The VL probe ignores unrelated events in the same time window."""
    monkeypatch.setattr(
        powerscale_func,
        "get_vlselect_endpoint",
        lambda _host: ("vlselect", "9471"),
    )
    marker = "powerscale-fvt-disabled-abc123"
    output = "\n".join([
        json.dumps({"_msg": f"OneFS test event {marker}"}),
        json.dumps({"_msg": "unrelated event"}),
    ])
    monkeypatch.setattr(
        powerscale_func,
        "run_on_kube_vip",
        lambda *_args: _result(output),
    )

    result = powerscale_func.query_powerscale_test_event(
        object(), marker, 10,
    )

    assert result == {"success": True, "count": 1, "error": ""}
