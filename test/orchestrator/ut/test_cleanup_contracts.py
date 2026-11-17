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
    """ORCH_UT_066: A created namespace is deleted when workload apply fails."""
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
    """ORCH_UT_067: Scheduler-state cleanup runs after a pending-job result."""
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
        slurm_jobs,
        "_context",
        lambda _host: ({}, [control, compute], control, {}),
    )

    node_state = ["idle"]

    def remote_command(_host, _row, command):
        commands.append(command)
        if "State=DRAIN" in command:
            node_state[0] = "drained"
        elif "State=RESUME" in command:
            node_state[0] = "idle"
        elif "sinfo" in command:
            return _result(stdout=node_state[0])
        elif "sbatch" in command:
            return _result(stdout="12345|PENDING")
        return _result()

    monkeypatch.setattr(slurm_jobs, "remote_command", remote_command)
    result = slurm_jobs.check_slurm_drain_queue_recovery(object())

    assert result["success"]
    assert any("scancel" in command for command in commands)
    assert any("RESUME" in command for command in commands)


def _storage_host(monkeypatch, mounts, delete=False):
    """Return a fake host whose omnia_config references nfs_k8s and nfs_slurm."""
    from library.functions import cleanup_func  # pylint: disable=import-outside-toplevel

    files = {
        "omnia_config.yml": {"service_k8s_cluster": [{"nfs_storage_name": "nfs_k8s"}],
                             "slurm_cluster": [{"nfs_storage_name": "nfs_slurm"}]},
        "storage_config.yml": {"mounts": mounts},
    }

    class _File:
        def __init__(self, path):
            self.is_file = True
            self.content_string = __import__("yaml").safe_dump(
                files[path.rsplit("/", 1)[-1]])

    host = SimpleNamespace(file=_File)
    monkeypatch.setattr(cleanup_func, "resolve_target_input_project_path", lambda _h: "/in")
    monkeypatch.setattr(cleanup_func, "load_test_config", lambda: {"cleanup_k8s": delete,
                                                                   "cleanup_slurm": delete})
    monkeypatch.setattr(cleanup_func, "run_on_host", lambda *_a, **_k: _result(rc=1))
    return cleanup_func, host


def test_cleanup_storage_without_a_mount_is_not_a_failure(monkeypatch):
    """ORCH_UT_BC_CLEANUP_001: a referenced storage with no mount (blank source) is skipped."""
    cleanup_func, host = _storage_host(monkeypatch, [])
    for check in (cleanup_func.check_cleanup_kubernetes, cleanup_func.check_cleanup_slurm):
        result = check(host)
        assert result["success"], result
        assert any("not configured in storage_config.yml" in str(value)
                   for _, value in result["fields"])


def test_cleanup_storage_still_fails_when_a_mount_is_attached(monkeypatch):
    """ORCH_UT_BC_CLEANUP_002: a configured mount that is still attached fails the check."""
    cleanup_func, host = _storage_host(monkeypatch, [
        {"name": "nfs_k8s", "source": "10.0.0.1:/k8s", "mount_point": "/opt/k8s"}])
    monkeypatch.setattr(cleanup_func, "run_on_host", lambda *_a, **_k: _result(rc=0))
    result = cleanup_func.check_cleanup_kubernetes(host)
    assert not result["success"]
    assert "nfs_k8s: storage still attached" in result["error"]
