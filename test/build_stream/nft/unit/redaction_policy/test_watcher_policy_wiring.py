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

# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-LOGGING-001.2, CG-SECRETS-001.7, CG-INPUT-001.9, CG-LOGGING-001.1
# ****

"""Playbook watcher builds its write-time redaction service from the policy (TC-UT-018)."""

import importlib.util
from pathlib import Path

import pytest
import yaml

from core.logs.redaction_policy import RedactionPolicyError, load_policy

WATCHER_PATH = (
    Path(__file__).parents[5] / "src" / "build_stream" / "app"
    / "playbook-watcher" / "playbook_watcher_service.py"
)
SPEC = importlib.util.spec_from_file_location(
    "redaction_policy_test_playbook_watcher_service", WATCHER_PATH
)
WATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WATCHER)

pytestmark = pytest.mark.unit


@pytest.fixture(name="logged")
def logged_fixture(monkeypatch) -> list:
    """Capture watcher log calls as (level, message) tuples."""
    calls: list = []
    monkeypatch.setattr(
        WATCHER, "log_secure_info",
        lambda level, message, *args, **kwargs: calls.append((level, message)),
    )
    return calls


def test_watcher_service_uses_operator_additions(monkeypatch, tmp_path, logged):
    """GIVEN operator additions THEN the watcher redacts them and logs no error."""
    config = tmp_path / "build_stream_config.yml"
    config.write_text(yaml.safe_dump({"redaction": {
        "additional_secret_key_names": ["vault_pass"],
        "additional_secret_patterns": [
            {"id": "zq-leak", "pattern": "Zq9Secret[0-9]{4}"},
            {"id": "zq-bad", "pattern": "Zq9Secret.*"},
        ]}}), encoding="utf-8")
    monkeypatch.setattr(WATCHER, "build_stream_config_path", lambda: config)
    service = WATCHER._build_redaction_service()
    assert service.redact("vault_pass: s3cret Zq9Secret1234") == (
        "vault_pass: ***REDACTED*** ***REDACTED***")
    assert len(logged) == 1
    assert logged[0][0] == "error"
    assert "zq-bad" in logged[0][1]
    assert "Zq9Secret" not in logged[0][1]


def test_invalid_project_name_falls_back_to_baseline(monkeypatch, logged):
    """GIVEN an invalid OMNIA_PROJECT_NAME THEN the baseline applies and one safe error is logged."""
    def _invalid_path():
        raise ValueError("OMNIA_PROJECT_NAME is not a valid single-segment name")

    monkeypatch.setattr(WATCHER, "build_stream_config_path", _invalid_path)
    service = WATCHER._build_redaction_service()
    assert service.redact("token=abc123") == "token=***REDACTED***"
    assert logged == [("error", "Invalid OMNIA_PROJECT_NAME; redaction additions ignored")]


def test_watcher_does_not_start_when_baseline_is_invalid(monkeypatch, tmp_path):
    """GIVEN an invalid baseline THEN building the service raises instead of running with fewer rules."""
    broken = tmp_path / "baseline.yml"
    broken.write_text("schema_version: 2\n", encoding="utf-8")
    monkeypatch.setattr(WATCHER, "build_stream_config_path", lambda: tmp_path / "absent.yml")
    monkeypatch.setattr(WATCHER, "load_policy", lambda path: load_policy(path, broken))
    with pytest.raises(RedactionPolicyError):
        WATCHER._build_redaction_service()
