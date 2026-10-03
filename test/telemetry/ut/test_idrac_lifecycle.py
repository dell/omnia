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

"""Contract tests for non-destructive iDRAC lifecycle reconciliation."""

import json
from pathlib import Path
import shlex
from types import SimpleNamespace

import yaml

from library.functions import idrac_func


REPO_ROOT = Path(__file__).resolve().parents[3]
IDRAC_ROLE = REPO_ROOT / "src/telemetry/roles/deploy_idrac_telemetry"
DEPLOY_PLAYBOOK = REPO_ROOT / "src/telemetry/playbooks/deploy/deploy.yml"
IDRAC_PLAYBOOK = (
    REPO_ROOT
    / "src/telemetry/playbooks/deploy/sources/deploy_idrac_telemetry.yml"
)
STATUS_TASKS = (
    REPO_ROOT / "src/telemetry/roles/common/tasks/write_telemetry_status.yml"
)
IDRAC_FVT = REPO_ROOT / "test/telemetry/fvt/deploy/sources/test_idrac.py"


def _read(path):
    return path.read_text(encoding="utf-8")


def _tasks(name):
    return yaml.safe_load(_read(IDRAC_ROLE / "tasks" / name))


def _task_by_name(tasks, name):
    return next(task for task in tasks if task.get("name") == name)


def test_idrac_role_selects_enable_and_disable_paths():
    """The role must route both boolean states to explicit task files."""
    tasks = _tasks("main.yml")
    enable = _task_by_name(tasks, "Enable iDRAC telemetry")
    disable = _task_by_name(tasks, "Disable iDRAC telemetry")

    assert enable["ansible.builtin.include_tasks"] == "enable.yml"
    assert "idrac_enabled" in enable["when"]
    assert disable["ansible.builtin.include_tasks"] == "disable.yml"
    assert "not (idrac_enabled" in disable["when"]


def test_full_deploy_always_invokes_idrac_reconciliation():
    """A false metrics flag must not skip the complete iDRAC source play."""
    plays = yaml.safe_load(_read(DEPLOY_PLAYBOOK))
    idrac = next(
        play for play in plays
        if play.get("name") == "Phase 2 | Deploy iDRAC telemetry"
    )

    assert idrac["ansible.builtin.import_playbook"].endswith(
        "deploy_idrac_telemetry.yml"
    )
    assert "when" not in idrac


def test_idrac_disable_is_noop_safe_and_idempotent():
    """Absent/already-zero StatefulSets must bypass the scale command."""
    tasks = _tasks("disable.yml")
    discover = _task_by_name(
        tasks, "Check if iDRAC telemetry StatefulSet exists"
    )
    scale = _task_by_name(
        tasks, "Scale down iDRAC telemetry StatefulSet to 0 replicas"
    )
    wait = _task_by_name(
        tasks, "Wait until all iDRAC telemetry pods have terminated"
    )

    assert "--ignore-not-found" in discover["ansible.builtin.command"]
    assert "--replicas=0" in scale["ansible.builtin.command"]
    assert any("idrac_sts_exists" in item for item in scale["when"])
    assert any("idrac_current_replicas" in item for item in scale["when"])
    assert wait["until"].endswith("== 0")


def test_idrac_disable_is_non_destructive_and_isolated():
    """Disable may only annotate, scale, and inspect iDRAC resources."""
    tasks = _tasks("disable.yml")
    commands = "\n".join(
        task.get("ansible.builtin.command", "")
        for task in tasks
    ).lower()
    source_play = _read(IDRAC_PLAYBOOK)

    assert "kubectl delete" not in commands
    assert "pvc" not in commands
    assert "secret" not in commands
    assert "configmap" not in commands
    assert "ldms" not in commands
    assert "victoria" not in commands
    assert "kafka" not in commands
    assert source_play.count("idrac_source_enabled | bool") == 2


def test_idrac_reenable_restores_retained_state():
    """Re-enable scales the retained object instead of recreating resources."""
    enable = _read(IDRAC_ROLE / "tasks/enable.yml")
    restore = _read(IDRAC_ROLE / "tasks/restore.yml")

    assert "desired-replicas" in enable
    assert "include_tasks: restore.yml" in enable
    assert "--replicas={{ idrac_replica_count }}" in restore
    assert "kubectl apply" not in restore
    assert "kubectl create" not in restore
    assert "kubectl delete" not in restore


def test_idrac_status_supports_deployed_disabled_and_failed():
    """Central status must distinguish configured disable from skip/failure."""
    deploy = _read(DEPLOY_PLAYBOOK)
    status = _read(STATUS_TASKS)

    assert "_idrac_ready | int) == (_idrac_desired | int)" in deploy
    assert "'disabled' if" in deploy
    assert "_idrac_reconcile_failed" in deploy
    assert "or 'disabled' in _all_results" in status
    assert "External component status values: deployed, disabled, failed" in status


def test_idrac_kafka_fvt_requires_a_fresh_record():
    """The enabled-state FVT must prove data flow, not only topic readiness."""
    fvt = _read(IDRAC_FVT)

    assert "verify_kafka_topic_ready(host, IDRAC_KAFKA_TOPIC)" in fvt
    assert "probe_fresh_idrac_kafka_records(host, timeout_seconds=90)" in fvt
    assert 'assert fresh["success"]' in fvt


def test_idrac_kafka_probe_sends_valid_consumer_json(monkeypatch):
    """Kafka Bridge consumer creation must contain one valid JSON object."""
    commands = []

    monkeypatch.setattr(idrac_func, "get_kafka_bridge_ip", lambda _host: "bridge")
    monkeypatch.setattr(idrac_func, "get_kafka_bridge_port", lambda _host: "8080")

    def _run(_host, command):
        commands.append(command)
        if command.endswith(
            "/records -H 'Accept: application/vnd.kafka.binary.v2+json'"
        ):
            return SimpleNamespace(
                rc=0,
                stdout=json.dumps([{
                    "topic": "idrac",
                    "partition": 0,
                    "offset": 1,
                    "timestamp": 2,
                    "value": "payload",
                }]),
                stderr="",
            )
        return SimpleNamespace(rc=0, stdout="", stderr="")

    monkeypatch.setattr(idrac_func, "run_on_kube_vip", _run)

    result = idrac_func.probe_fresh_idrac_kafka_records(
        object(), timeout_seconds=1,
    )

    create_command = commands[0]
    arguments = shlex.split(create_command)
    payload = arguments[arguments.index("-d") + 1]
    assert json.loads(payload) == {
        "name": "fresh-record-check",
        "format": "binary",
        "auto.offset.reset": "latest",
        "enable.auto.commit": False,
    }
    assert result["success"]
