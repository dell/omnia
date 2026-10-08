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

"""Contract tests for non-destructive UFM lifecycle reconciliation."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
UFM_ROLE = REPO_ROOT / "src/telemetry/roles/deploy_ufm"
DEPLOY_PLAYBOOK = REPO_ROOT / "src/telemetry/playbooks/deploy/deploy.yml"
UFM_PLAYBOOK = (
    REPO_ROOT
    / "src/telemetry/playbooks/deploy/sources/deploy_ufm.yml"
)
STATUS_TASKS = (
    REPO_ROOT / "src/telemetry/roles/common/tasks/write_telemetry_status.yml"
)


def _read(path):
    return path.read_text(encoding="utf-8")


def _tasks(name):
    return yaml.safe_load(_read(UFM_ROLE / "tasks" / name))


def _task_by_name(tasks, name):
    return next(task for task in tasks if task.get("name") == name)


def test_ufm_role_selects_enable_and_disable_paths():
    """The role must route both boolean states to explicit task files."""
    tasks = _tasks("main.yml")
    enable = _task_by_name(tasks, "Enable UFM telemetry")
    disable = _task_by_name(tasks, "Disable UFM telemetry")

    assert enable["ansible.builtin.include_tasks"] == "enable.yml"
    assert "ufm_enabled" in enable["when"]
    assert disable["ansible.builtin.include_tasks"] == "disable.yml"
    assert "not (ufm_enabled" in disable["when"]


def test_full_deploy_always_invokes_ufm_reconciliation():
    """A false metrics flag must not skip the complete UFM source play."""
    plays = yaml.safe_load(_read(DEPLOY_PLAYBOOK))
    ufm = next(
        play for play in plays
        if play.get("name") == "Phase 2 | Deploy UFM telemetry"
    )

    assert ufm["ansible.builtin.import_playbook"].endswith(
        "deploy_ufm.yml"
    )
    assert "when" not in ufm


def test_ufm_disable_is_noop_safe_and_idempotent():
    """Absent UFM services must bypass the delete command."""
    tasks = _tasks("disable.yml")
    discover = _task_by_name(
        tasks, "Check if UFM external service exists"
    )
    delete_svc = _task_by_name(
        tasks, "Delete UFM external service (preserving credentials secret)"
    )

    assert "--ignore-not-found" in discover["ansible.builtin.command"]
    assert "ufm_svc_exists" in str(delete_svc["when"])


def test_ufm_disable_is_non_destructive():
    """Disable may only remove service/endpoints/vmscrape, not the secret."""
    text = _read(UFM_ROLE / "tasks/disable.yml").lower()

    # Must not delete the credentials secret
    assert "kubectl delete secret" not in text
    # Must not delete PVCs or configmaps
    assert "persistentvolumeclaim" not in text
    assert "configmap" not in text
    # References the correct service name variable
    assert "ufm_external_service_name" in text


def test_ufm_disable_preserves_credentials_secret():
    """Disable deletes service/endpoints/vmscrape but preserves secret."""
    tasks = _tasks("disable.yml")
    commands = "\n".join(
        task.get("ansible.builtin.command", "")
        for task in tasks
    ).lower()

    # Should delete service and endpoints
    assert "delete service" in commands
    assert "delete endpoints" in commands
    # Should delete VMServiceScrape (stops VMAgent from scraping)
    assert "delete vmservicescrape" in commands
    # Must not delete secret
    assert "delete secret" not in commands


def test_ufm_reenable_restores_retained_state():
    """Re-enable reapplies service manifests using retained secret."""
    enable = _read(UFM_ROLE / "tasks/enable.yml")
    restore = _read(UFM_ROLE / "tasks/restore.yml")

    assert "ufm_credentials_secret_name" in enable
    assert "ufm_is_reenable" in enable
    assert "include_tasks: restore.yml" in enable
    assert "include_tasks: generate_manifests.yml" in restore
    assert "kubectl delete" not in restore


def test_ufm_reenable_skips_validation():
    """Re-enable must skip credential and endpoint validation."""
    enable = _read(UFM_ROLE / "tasks/enable.yml")
    tasks = _tasks("enable.yml")

    # All validation tasks should have ufm_is_reenable guard
    validate_tasks = [
        t for t in tasks
        if t.get("name", "").startswith("Validate UFM")
    ]
    for task in validate_tasks:
        when_clause = str(task.get("when", ""))
        assert "ufm_is_reenable" in when_clause, (
            f"Validation task '{task['name']}' lacks ufm_is_reenable guard"
        )

    # Secret and service checks used for re-enable detection
    assert "ufm_enable_secret_check" in enable
    assert "ufm_enable_svc_check" in enable


def test_ufm_status_supports_deployed_and_disabled():
    """Central status must distinguish configured disable from skip/failure."""
    deploy = _read(DEPLOY_PLAYBOOK)
    status = _read(STATUS_TASKS)

    assert "_deploy_result_ufm_metrics" in deploy
    assert "_deploy_result_ufm_logs" in deploy
    assert "'disabled' if not (_ufm_m_on | bool)" in deploy
    assert "'disabled' if not (_ufm_l_on | bool)" in deploy
    assert "or 'disabled' in _all_results" in status
    assert "External component status values: deployed, disabled, failed" in status


def test_ufm_source_playbook_determines_enabled_state():
    """The source playbook must derive ufm_source_enabled before roles."""
    source_play = _read(UFM_PLAYBOOK)

    assert "ufm_source_enabled" in source_play
    assert "telemetry_sources.ufm.metrics_enabled" in source_play
