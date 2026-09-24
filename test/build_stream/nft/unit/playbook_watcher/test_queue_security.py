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

"""Security regression tests for the root playbook watcher queue."""

import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from common.queue_auth import (
    create_signed_envelope,
    read_signed_payload,
    write_signed_payload,
)

KEY = b"w" * 32
JOB_ID = "018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"
REQUEST_ID = "019bf590-1234-7890-abcd-ef1234567890"
WATCHER_PATH = (
    Path(__file__).resolve().parents[5]
    / "src"
    / "build_stream"
    / "app"
    / "playbook-watcher"
    / "playbook_watcher_service.py"
)
SPEC = importlib.util.spec_from_file_location(
    "playbook_watcher_service", WATCHER_PATH
)
WATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WATCHER)


def _local_repo_payload(**overrides):
    payload = {
        "request_id": REQUEST_ID,
        "job_id": JOB_ID,
        "stage_name": "create-local-repository",
        "command_type": "ansible-playbook",
        "playbook_path": "repo_manager.yml",
        "extra_vars": {"job_id": JOB_ID, "attempt": 1},
        "tags": "execute",
        "correlation_id": REQUEST_ID,
        "timeout_minutes": 30,
        "submitted_at": "2026-09-23T00:00:00Z",
    }
    payload.update(overrides)
    return payload


def _configure_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(WATCHER, "_QUEUE_AUTH_KEY", KEY)
    monkeypatch.setattr(WATCHER, "REQUESTS_DIR", tmp_path / "requests")
    monkeypatch.setattr(WATCHER, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(WATCHER, "PROCESSING_DIR", tmp_path / "processing")
    monkeypatch.setattr(WATCHER, "ARCHIVE_DIR", tmp_path / "archive")
    monkeypatch.setattr(WATCHER, "REPLAY_STATE_DIR", tmp_path / "consumed")
    for directory in (
        WATCHER.REQUESTS_DIR,
        WATCHER.RESULTS_DIR,
        WATCHER.PROCESSING_DIR,
        WATCHER.ARCHIVE_DIR / "requests",
        WATCHER.ARCHIVE_DIR / "results",
        WATCHER.REPLAY_STATE_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def test_unsigned_request_never_reaches_execution(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)
    request_path = WATCHER.REQUESTS_DIR / "forged.json"
    request_path.write_text(
        json.dumps(_local_repo_payload()), encoding="utf-8"
    )
    execute_playbook = Mock()
    execute_molecule = Mock()
    monkeypatch.setattr(WATCHER, "execute_playbook", execute_playbook)
    monkeypatch.setattr(WATCHER, "execute_molecule", execute_molecule)

    WATCHER.process_request(request_path)

    execute_playbook.assert_not_called()
    execute_molecule.assert_not_called()


def test_tampered_signed_request_is_rejected(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)
    request_path = tmp_path / "tampered.json"
    envelope = create_signed_envelope(
        _local_repo_payload(), KEY, purpose="request"
    )
    envelope["payload"]["tags"] = "cleanup"
    request_path.write_text(json.dumps(envelope), encoding="utf-8")

    assert WATCHER.parse_request_file(request_path) is None


def test_request_selected_inventory_path_is_rejected(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)
    request_path = tmp_path / "inventory.json"
    write_signed_payload(
        request_path,
        _local_repo_payload(inventory_file_path="/tmp/attacker"),
        KEY,
        purpose="request",
    )

    assert WATCHER.parse_request_file(request_path) is None


@pytest.mark.parametrize(
    ("stage", "playbook", "tags", "extra_vars"),
    [
        (
            "create-local-repository",
            "repo_manager.yml",
            "execute",
            {"job_id": JOB_ID, "attempt": 1},
        ),
        ("build-image", "image_build_manager.yml", "execute", {"job_id": JOB_ID}),
        (
            "deploy",
            "orchestrator.yml",
            "provision",
            {
                "job_id": JOB_ID,
                "image_key": "image-1",
                "image_group_id": "image-1",
                "attempt": 1,
            },
        ),
        (
            "restart",
            "orchestrator.yml",
            "pxeboot",
            {
                "job_id": JOB_ID,
                "image_group_id": "image-1",
                "attempt": 1,
                "enable_build_stream": True,
            },
        ),
        (
            "cleanup",
            "image_build_manager.yml",
            "cleanup_images",
            {"cleanup_image_pattern": "image-1", "skip_approval": "true"},
        ),
    ],
)
def test_legitimate_playbook_contracts_remain_accepted(
    monkeypatch, tmp_path, stage, playbook, tags, extra_vars
):
    _configure_paths(monkeypatch, tmp_path)
    request_path = tmp_path / f"{stage}.json"
    payload = _local_repo_payload(
        stage_name=stage,
        playbook_path=playbook,
        tags=tags,
        extra_vars=extra_vars,
    )
    write_signed_payload(
        request_path, payload, KEY, purpose="request"
    )

    parsed = WATCHER.parse_request_file(request_path)

    assert parsed is not None
    assert parsed["playbook_name"] == playbook


def test_legitimate_validation_contract_remains_accepted(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)
    request_path = tmp_path / "validate.json"
    payload = {
        "request_id": f"validate_{JOB_ID}_20260923_120000",
        "job_id": JOB_ID,
        "stage_type": "validate",
        "command_type": "test_automation",
        "scenario_names": ["all"],
        "test_suite": "",
        "timeout_minutes": 150,
        "artifact_dir": f"/opt/omnia/build_stream_root/{JOB_ID}",
        "config_path": "/opt/omnia/build_stream/validate/config.yml",
        "correlation_id": REQUEST_ID,
        "submitted_at": "2026-09-23T00:00:00Z",
        "attempt": 1,
    }
    write_signed_payload(
        request_path, payload, KEY, purpose="request"
    )

    parsed = WATCHER.parse_request_file(request_path)

    assert parsed is not None
    assert parsed["stage_type"] == "validate"


def test_stage_playbook_or_tag_mismatch_is_rejected(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)
    request_path = tmp_path / "mismatch.json"
    write_signed_payload(
        request_path,
        _local_repo_payload(playbook_path="orchestrator.yml"),
        KEY,
        purpose="request",
    )

    assert WATCHER.parse_request_file(request_path) is None


def test_unknown_command_type_is_rejected(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)
    request_path = tmp_path / "unknown.json"
    write_signed_payload(
        request_path,
        _local_repo_payload(command_type="unknown"),
        KEY,
        purpose="request",
    )

    assert WATCHER.parse_request_file(request_path) is None


def test_request_replay_is_rejected(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)

    assert WATCHER.claim_request_id(REQUEST_ID) is True
    assert WATCHER.claim_request_id(REQUEST_ID) is False


def test_replayed_request_does_not_mint_a_workflow_result(
    monkeypatch, tmp_path
):
    _configure_paths(monkeypatch, tmp_path)
    request_path = WATCHER.REQUESTS_DIR / "replayed.json"
    write_signed_payload(
        request_path,
        _local_repo_payload(),
        KEY,
        purpose="request",
    )
    assert WATCHER.claim_request_id(REQUEST_ID) is True
    execute_playbook = Mock()
    monkeypatch.setattr(WATCHER, "execute_playbook", execute_playbook)

    WATCHER.process_request(request_path)

    execute_playbook.assert_not_called()
    assert not list(WATCHER.RESULTS_DIR.glob("*.json"))


def test_watcher_writes_authenticated_result(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)
    result = {
        "job_id": JOB_ID,
        "stage_name": "build-image",
        "request_id": REQUEST_ID,
        "status": "success",
    }

    assert WATCHER.write_result_file(result, "result.json") is True
    assert read_signed_payload(
        WATCHER.RESULTS_DIR / "result.json", KEY, purpose="result"
    ) == result
