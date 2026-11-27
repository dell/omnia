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

"""Unit contracts: the Slurm OpenMPI job never waits for ever on a node that is down."""

from types import SimpleNamespace

from library.functions import _workload_helpers as workload
from library.functions import slurm_jobs_pxeboot_func as slurm_jobs
from library.vars.pxeboot_vars import PXEBOOT_COMMANDS

NODES = [
    {"HOSTNAME": "slurm-node-1", "ADMIN_IP": "192.0.2.11"},
    {"HOSTNAME": "slurm-node-2", "ADMIN_IP": "192.0.2.12"},
]


def _result(rc=0, stdout="", stderr=""):
    return SimpleNamespace(rc=rc, stdout=stdout, stderr=stderr)


def _sinfo(states):
    """Return a remote_command stub that answers the sinfo queries with ``states``."""
    commands = []

    def remote_command(_host, _row, command):
        commands.append(command)
        if "--format='%N|%P|%T|%a'" in command:
            return _result(stdout="".join(
                f"{name}|batch|{state}|up\n" for name, state, _reason in states))
        if "%N|%E" in command:
            return _result(stdout="".join(f"{name}|{reason}\n" for name, _s, reason in states))
        raise AssertionError(f"Unexpected command: {command}")

    return commands, remote_command


def test_openmpi_commands_are_bounded():
    """ORCH_UT_385: the compile and the job commands have a time limit and no endless queue."""
    job = PXEBOOT_COMMANDS["openmpi_job"]
    compile_command = PXEBOOT_COMMANDS["openmpi_compile"]
    for command in (job, compile_command):
        assert command.startswith("timeout %s srun ")
        assert "--immediate=%s" in command
    assert "--time=%s" in job and "--job-name=%s" in job


def test_down_node_is_reported_with_its_reason(monkeypatch):
    """ORCH_UT_386: a node that is down* is named with its state and Slurm's reason."""
    _commands, remote = _sinfo([
        ("slurm-node-1", "idle", "none"),
        ("slurm-node-2", "down*", "Not responding"),
    ])
    monkeypatch.setattr(workload, "remote_command", remote)
    problems = workload.not_ready_computes(object(), {"ADMIN_IP": "192.0.2.1"}, NODES)
    assert len(problems) == 1
    assert problems[0].startswith("slurm-node-2 (state=down*")
    assert "Not responding" in problems[0]


def test_not_responding_idle_node_is_not_ready(monkeypatch):
    """ORCH_UT_387: idle* (slurmd stopped, not yet marked down) cannot take a job."""
    _commands, remote = _sinfo([("slurm-node-1", "idle", "none"), ("slurm-node-2", "idle*", "none")])
    monkeypatch.setattr(workload, "remote_command", remote)
    problems = workload.not_ready_computes(object(), {"ADMIN_IP": "192.0.2.1"}, NODES)
    assert [item.split(" ", 1)[0] for item in problems] == ["slurm-node-2"]


def test_ready_and_busy_nodes_pass(monkeypatch):
    """ORCH_UT_388: idle, mixed and allocated nodes are ready; a missing node is not."""
    _commands, remote = _sinfo([("slurm-node-1", "mixed", "none"), ("slurm-node-2", "allocated", "none")])
    monkeypatch.setattr(workload, "remote_command", remote)
    assert workload.not_ready_computes(object(), {"ADMIN_IP": "192.0.2.1"}, NODES) == []
    _commands, remote = _sinfo([("slurm-node-1", "idle", "none")])
    monkeypatch.setattr(workload, "remote_command", remote)
    missing = workload.not_ready_computes(object(), {"ADMIN_IP": "192.0.2.1"}, NODES)
    assert len(missing) == 1 and missing[0].startswith("slurm-node-2 (state=missing")


def test_openmpi_job_fails_at_once_when_a_node_is_down(monkeypatch):
    """ORCH_UT_389: no srun is sent and no job is left when a target node is down."""
    commands, sinfo = _sinfo([
        ("slurm-node-1", "idle", "none"),
        ("slurm-node-2", "down*", "Not responding"),
    ])
    monkeypatch.setattr(workload, "remote_command", sinfo)
    monkeypatch.setattr(slurm_jobs, "_require_functional", lambda _summary: None)
    monkeypatch.setattr(
        slurm_jobs, "_context",
        lambda _host: ({"features": {"openmpi": True}}, NODES, {"ADMIN_IP": "192.0.2.1"}, {}),
    )
    monkeypatch.setattr(slurm_jobs, "_compute_rows", lambda rows: rows)
    monkeypatch.setattr(slurm_jobs, "remote_command", sinfo)
    result = slurm_jobs.check_slurm_openmpi_job(object())
    assert result["success"] is False
    assert "slurm-node-2" in result["error"] and "Not responding" in result["error"]
    assert not any("srun" in command for command in commands)
