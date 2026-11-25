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

"""The log API builds its redaction service from the policy (TC-UT-018)."""

import pytest
import yaml

from api.logs import dependencies
from core.logs.redaction_policy import RedactionPolicyError, load_policy

pytestmark = pytest.mark.unit


@pytest.fixture(name="logged")
def logged_fixture(monkeypatch):
    """Fresh cached service per test; captures log calls and restores the cache afterwards."""
    dependencies.get_redaction_service.cache_clear()
    calls: list = []
    monkeypatch.setattr(
        dependencies, "log_secure_info",
        lambda level, message, *args, **kwargs: calls.append((level, message)),
    )
    yield calls
    dependencies.get_redaction_service.cache_clear()


def test_service_applies_operator_additions_and_logs_errors(monkeypatch, tmp_path, logged):
    """GIVEN operator additions with one invalid entry THEN the valid ones apply and the error is logged."""
    config = tmp_path / "build_stream_config.yml"
    config.write_text(yaml.safe_dump({"redaction": {
        "additional_secret_key_names": ["vault_pass"],
        "additional_secret_patterns": [
            {"id": "acme-token", "pattern": "acme-[A-Za-z0-9]{16}"},
            {"id": "gitlab-token", "pattern": "Zq9Secret[0-9]{4}"},
        ]}}), encoding="utf-8")
    monkeypatch.setattr(dependencies, "build_stream_config_path", lambda: config)
    service = dependencies.get_redaction_service()
    assert service.redact("vault_pass: s3cret acme-0123456789abcdef") == (
        "vault_pass: ***REDACTED*** ***REDACTED***")
    assert service.redact("token=abc123") == "token=***REDACTED***"
    assert [level for level, _ in logged] == ["error"]
    assert "gitlab-token" in logged[0][1]
    assert "Zq9Secret" not in logged[0][1]


def test_invalid_project_name_falls_back_to_baseline(monkeypatch, logged):
    """GIVEN an invalid OMNIA_PROJECT_NAME THEN the baseline applies and one safe error is logged."""
    def _invalid_path():
        raise ValueError("OMNIA_PROJECT_NAME is not a valid single-segment name")

    monkeypatch.setattr(dependencies, "build_stream_config_path", _invalid_path)
    service = dependencies.get_redaction_service()
    assert service.redact("token=abc123") == "token=***REDACTED***"
    assert logged == [("error", "Invalid OMNIA_PROJECT_NAME; redaction additions ignored")]


def test_broken_baseline_stops_service_construction(monkeypatch, tmp_path, logged):
    """GIVEN an invalid baseline THEN building the service raises."""
    broken = tmp_path / "baseline.yml"
    broken.write_text("schema_version: 2\n", encoding="utf-8")
    monkeypatch.setattr(dependencies, "build_stream_config_path", lambda: tmp_path / "x.yml")
    monkeypatch.setattr(dependencies, "load_policy", lambda path: load_policy(path, broken))
    with pytest.raises(RedactionPolicyError):
        dependencies.get_redaction_service()
