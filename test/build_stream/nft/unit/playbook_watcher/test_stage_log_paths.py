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

# pylint: disable=redefined-outer-name,protected-access,unused-argument

"""Unit tests for playbook-watcher stage log paths and attempt numbering.

Playbooks log to ``/var/log/omnia/<domain>/`` exactly like a manual run and
the log is copied to ``<OMNIA_DATA_PATH>/build_stream/logs/<job_id>/``. Every
result reports the copy, named with the stage attempt, on success, failure,
timeout, and system error.
"""

import importlib.util
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

WATCHER_PATH = (
    Path(__file__).parents[5] / "src" / "build_stream" / "app"
    / "playbook-watcher" / "playbook_watcher_service.py"
)
SPEC = importlib.util.spec_from_file_location(
    "stage_log_test_playbook_watcher_service", WATCHER_PATH
)
WATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WATCHER)

pytestmark = pytest.mark.unit

PLAYBOOK = "/opt/src/image_build_manager/playbooks/image_build_manager.yml"


@pytest.fixture
def domain_root(tmp_path, monkeypatch):
    """Redirect /var/log/omnia to a temporary directory."""
    root = tmp_path / "var" / "log" / "omnia"
    monkeypatch.setattr(WATCHER, "PLAYBOOK_LOG_BASE_DIR", root)
    return root


@pytest.fixture
def log_root(tmp_path, monkeypatch, domain_root):
    """Redirect the BuildStream job log root to a temporary directory."""
    root = tmp_path / "build_stream" / "logs"
    monkeypatch.setattr(WATCHER, "HOST_LOG_BASE_DIR", root)
    monkeypatch.setattr(WATCHER.time, "sleep", lambda _seconds: None)
    return root


def _domain_copy(domain_root, reported):
    """Return the /var/log/omnia/image_build_manager/ original of a copy."""
    return domain_root / "image_build_manager" / Path(reported).name


def _request(job_id, attempt=None, stage="build-image"):
    extra_vars = {"job_id": job_id}
    if attempt is not None:
        extra_vars["attempt"] = attempt
    return {
        "job_id": job_id,
        "stage_name": stage,
        "playbook_name": "image_build_manager.yml",
        "extra_vars": extra_vars,
    }


def _execute(request, run):
    with patch.object(WATCHER, "map_playbook_name_to_path", return_value=PLAYBOOK), \
         patch.object(WATCHER, "validate_command", return_value=True), \
         patch.object(WATCHER.subprocess, "run", side_effect=run):
        return WATCHER.execute_playbook(request)


@pytest.mark.parametrize("value,expected", [
    (1, 1), (11, 11), (1000, 1000),
    (0, 1), (-3, 1), (1001, 1), (True, 1), ("2", 1), (None, 1), (2.0, 1),
])
def test_sanitize_attempt(value, expected):
    """Attempts above the old limit of 10 are preserved; invalid ones reset to 1."""
    assert WATCHER.sanitize_attempt(value) == expected


def test_stage_log_path_is_under_var_log_omnia_domain(domain_root):
    """Ansible writes to /var/log/omnia/<domain>/<stage>_<playbook>_<ts>_attempt<N>.log."""
    started = datetime(2026, 10, 6, 1, 2, 3, tzinfo=timezone.utc)

    path = WATCHER.build_stage_log_path(
        "orchestrator", "deploy", "orchestrator.yml", started, 4
    )

    assert path == (
        domain_root / "orchestrator"
        / "deploy_orchestrator.yml_20261006_010203_attempt4.log"
    )
    assert path.parent.is_dir()


def test_log_locations():
    """Playbooks log to /var/log/omnia; copies go to <data>/build_stream/logs."""
    assert WATCHER.PLAYBOOK_LOG_BASE_DIR == Path("/var/log/omnia")
    assert WATCHER.HOST_LOG_BASE_DIR.parts[-2:] == ("build_stream", "logs")
    assert "log/build_stream" not in str(WATCHER.HOST_LOG_BASE_DIR)


@pytest.mark.parametrize("playbook,domain", [
    ("/src/image_build_manager/playbooks/image_build_manager.yml", "image_build_manager"),
    ("/src/repo_manager/playbooks/repo_operations/repo_sync.yml", "repo_manager"),
    ("/tmp/no_domain.yml", "build_stream"),
])
def test_domain_extraction(playbook, domain):
    """The domain comes from src/<domain>/playbooks/; unknown falls back to build_stream."""
    assert WATCHER._extract_domain_from_playbook_path(playbook) == domain


def test_publish_keeps_domain_log_and_copies(log_root, domain_root):
    """The /var/log/omnia log stays in place and an identical copy is reported."""
    domain_log = domain_root / "orchestrator" / "deploy_x.yml_ts_attempt1.log"
    domain_log.parent.mkdir(parents=True)
    domain_log.write_text("PLAY\n", encoding="utf-8")

    reported = WATCHER.publish_stage_log(domain_log, "job-9", ["done"])

    assert reported == str(log_root / "job-9" / domain_log.name)
    assert domain_log.is_file()
    assert Path(reported).read_text(encoding="utf-8") == domain_log.read_text(
        encoding="utf-8"
    )
    assert "[playbook-watcher] done" in domain_log.read_text(encoding="utf-8")


def test_publish_reports_domain_log_when_copy_fails(log_root, domain_root):
    """If the copy fails, the existing /var/log/omnia log is reported."""
    domain_log = domain_root / "x" / "a.log"
    domain_log.parent.mkdir(parents=True)

    with patch.object(WATCHER.shutil, "copy2", side_effect=OSError("ro fs")):
        reported = WATCHER.publish_stage_log(domain_log, "job-9", ["done"])

    assert reported == str(domain_log)


def test_success_reports_ansible_log_path_with_attempt(log_root, domain_root):
    """Ansible logs to /var/log/omnia; the reported copy carries the retry attempt."""
    job_id = str(uuid.uuid4())
    seen = {}

    def _run(cmd, **kwargs):
        seen["env_log"] = kwargs["env"]["ANSIBLE_LOG_PATH"]
        seen["extra_vars"] = cmd[cmd.index("--extra-vars") + 1]
        Path(seen["env_log"]).write_text("PLAY RECAP\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)

    result = _execute(_request(job_id, attempt=3), _run)

    assert result["status"] == "success"
    assert result["attempt"] == 3
    log_path = Path(result["log_file_path"])
    assert Path(seen["env_log"]) == _domain_copy(domain_root, log_path)
    assert Path(seen["env_log"]).is_file()
    assert log_path.parent == log_root / job_id
    assert log_path.name.startswith("build-image_image_build_manager.yml_")
    assert log_path.name.endswith("_attempt3.log")
    content = log_path.read_text(encoding="utf-8")
    assert "PLAY RECAP" in content
    assert "attempt=3 status=success" in content
    assert '"attempt": 3' in seen["extra_vars"]


def test_failure_without_ansible_output_still_reports_existing_log(log_root, domain_root):
    """A failed run that wrote no log still returns an existing log file."""
    job_id = str(uuid.uuid4())

    result = _execute(
        _request(job_id, attempt=2),
        lambda cmd, **_: subprocess.CompletedProcess(cmd, 2),
    )

    log_path = Path(result["log_file_path"])
    assert result["status"] == "failed"
    assert result["error_code"] == "PLAYBOOK_EXECUTION_FAILED"
    assert str(log_path) in result["error_summary"]
    assert log_path.parent == log_root / job_id
    assert log_path.is_file()
    assert _domain_copy(domain_root, log_path).is_file()
    assert "attempt=2 status=failed exit_code=2" in log_path.read_text(encoding="utf-8")


def test_timeout_reports_log_path(log_root, domain_root):
    """A timed-out playbook reports the same per-attempt log path."""
    job_id = str(uuid.uuid4())

    def _timeout(cmd, **kwargs):
        Path(kwargs["env"]["ANSIBLE_LOG_PATH"]).write_text("TASK [x]\n", encoding="utf-8")
        raise subprocess.TimeoutExpired(cmd, 1)

    result = _execute(_request(job_id, attempt=5), _timeout)

    log_path = Path(result["log_file_path"])
    assert result["status"] == "failed"
    assert result["error_code"] == "PLAYBOOK_TIMEOUT"
    assert result["attempt"] == 5
    assert log_path.parent == log_root / job_id
    assert log_path.name.endswith("_attempt5.log")
    content = log_path.read_text(encoding="utf-8")
    assert "TASK [x]" in content
    assert "error_code=PLAYBOOK_TIMEOUT" in content
    assert _domain_copy(domain_root, log_path).read_text(encoding="utf-8") == content
    assert result["log_file_path"] in result["error_summary"]


def test_system_error_reports_log_path(log_root):
    """An OSError launching ansible-playbook still reports the log path."""
    job_id = str(uuid.uuid4())

    def _boom(cmd, **kwargs):
        raise OSError("ansible-playbook not found")

    result = _execute(_request(job_id), _boom)

    assert result["error_code"] == "SYSTEM_ERROR"
    assert result["attempt"] == 1
    assert Path(result["log_file_path"]).is_file()
    assert result["log_file_path"] in result["error_summary"]


def test_missing_attempt_defaults_to_one(log_root):
    """Requests without an attempt are logged as attempt 1."""
    result = _execute(
        _request(str(uuid.uuid4())),
        lambda cmd, **_: subprocess.CompletedProcess(cmd, 0),
    )

    assert result["log_file_path"].endswith("_attempt1.log")


def test_rejected_request_returns_failed_result():
    """A request rejected before execution reports a failed stage."""
    job_id = str(uuid.uuid4())

    result = WATCHER.build_rejected_result(
        {"job_id": job_id, "stage_name": "deploy"}, ValueError("bad playbook")
    )

    assert result["job_id"] == job_id
    assert result["stage_name"] == "deploy"
    assert result["status"] == "failed"
    assert result["error_code"] == "REQUEST_REJECTED"
    assert "bad playbook" in result["error_summary"]


def test_process_request_writes_result_when_execution_rejected(tmp_path, monkeypatch):
    """A rejected request still produces a result file (stage never hangs)."""
    job_id = str(uuid.uuid4())
    for name in ("REQUESTS_DIR", "RESULTS_DIR", "PROCESSING_DIR"):
        directory = tmp_path / name
        directory.mkdir()
        monkeypatch.setattr(WATCHER, name, directory)
    monkeypatch.setattr(WATCHER, "ARCHIVE_DIR", tmp_path / "archive")
    (tmp_path / "archive" / "requests").mkdir(parents=True)
    request_file = WATCHER.REQUESTS_DIR / f"{job_id}.json"
    request = {"job_id": job_id, "stage_name": "deploy", "playbook_path": "x.yml"}
    request_file.write_text("{}", encoding="utf-8")

    with patch.object(WATCHER, "parse_request_file", return_value=request), \
         patch.object(WATCHER, "execute_playbook", side_effect=ValueError("nope")):
        WATCHER.process_request(request_file)

    result = (WATCHER.RESULTS_DIR / request_file.name).read_text(encoding="utf-8")
    assert '"status": "failed"' in result
    assert "REQUEST_REJECTED" in result


def test_validate_timeout_logs_to_orchestrator_domain_and_copies(
    tmp_path, monkeypatch, log_root, domain_root,
):
    """Validate-stage test output is logged and copied on timeout too."""
    job_id = str(uuid.uuid4())
    monkeypatch.setattr(WATCHER, "ARTIFACTS_DIR", tmp_path / "artifacts")
    request = {
        "job_id": job_id,
        "stage_type": "validate",
        "command_type": "test_automation",
        "config_path": "/opt/omnia/build_stream/validate/config.yml",
        "scenario_names": ["validate"],
        "attempt": 2,
    }

    def _timeout(cmd, **_kwargs):
        raise subprocess.TimeoutExpired(cmd, 1, output="partial out", stderr="err")

    with patch.object(WATCHER, "_resolve_orchestrator_report_dir", return_value=tmp_path), \
         patch.object(WATCHER.subprocess, "run", side_effect=_timeout):
        result = WATCHER.execute_molecule(request)

    log_path = Path(result["log_file_path"])
    assert result["exit_code"] == 124
    assert result["attempt"] == 2
    assert log_path.parent == log_root / job_id
    assert log_path.name.startswith("validate_run_validation.sh_")
    assert log_path.name.endswith("_attempt2.log")
    original = domain_root / "orchestrator" / log_path.name
    assert original.is_file()
    assert "partial out" in log_path.read_text(encoding="utf-8")
