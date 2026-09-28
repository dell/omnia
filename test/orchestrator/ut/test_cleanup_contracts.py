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

"""Unit contracts proving state-changing probes restore temporary state."""

from types import SimpleNamespace

from library.functions import kubernetes_storage_pxeboot_func as kubernetes_storage
from library.functions import slurm_jobs_pxeboot_func as slurm_jobs


def _result(rc=0, stdout="", stderr=""):
    return SimpleNamespace(rc=rc, stdout=stdout, stderr=stderr)


def test_kubernetes_workload_cleanup_runs_after_apply_failure(monkeypatch):
    """ORCH_UT_009: A created namespace is deleted when workload apply fails."""
    commands = []

    def remote_command(_host, _row, command):
        commands.append(command)
        if "create namespace" in command:
            return _result()
        if "base64" in command:
            return _result(rc=1, stderr="apply failed")
        if "delete namespace" in command:
            return _result()
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(
        kubernetes_storage, "_test_namespace", lambda: "omnia-fvt-fixed"
    )
    monkeypatch.setattr(kubernetes_storage, "remote_command", remote_command)

    success, fields, error = kubernetes_storage._run_functional_manifest(
        object(),
        {"HOSTNAME": "kcp1", "ADMIN_IP": "192.0.2.10"},
    )

    assert not success
    assert "apply" in error.lower()
    assert ("Cleanup", "passed") in fields
    assert any("delete namespace" in command for command in commands)


def test_slurm_drain_probe_always_cancels_job_and_resumes_node(monkeypatch):
    """ORCH_UT_010: Scheduler-state cleanup runs after a pending-job result."""
    commands = []
    control = {
        "HOSTNAME": "slurmctl",
        "ADMIN_IP": "192.0.2.20",
        "EXPECTED_FUNCTIONAL_GROUP": "slurm_control_node_rhel_10_0_x86_64",
    }
    compute = {
        "HOSTNAME": "nid001",
        "ADMIN_IP": "192.0.2.21",
        "EXPECTED_FUNCTIONAL_GROUP": "slurm_node_rhel_10_0_x86_64",
    }
    monkeypatch.setattr(
        slurm_jobs, "marker_is_authorized", lambda marker: marker == "disruptive"
    )
    monkeypatch.setattr(
        slurm_jobs,
        "_context",
        lambda _host: ({}, [control, compute], control, {}),
    )

    def remote_command(_host, _row, command):
        commands.append(command)
        if "sbatch" in command:
            return _result(stdout="12345|PENDING")
        return _result()

    monkeypatch.setattr(slurm_jobs, "remote_command", remote_command)
    result = slurm_jobs.check_slurm_drain_queue_recovery(object())

    assert result["success"]
    assert any("scancel" in command for command in commands)
    assert any("RESUME" in command for command in commands)
