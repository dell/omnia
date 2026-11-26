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

"""The log API and audit logging share one policy-built redaction service (TC-UT-018)."""

import logging

import pytest
import yaml

from api import logging_utils
from api.logs import dependencies
from core.logs.redaction_patterns import REDACTION_SUPPRESSED_LINE
from core.logs.redaction_policy import RedactionPolicyError, load_policy
from orchestrator.cleanup import retention_config

pytestmark = pytest.mark.unit

ACME = "acme-0123456789abcdef"  # gitleaks:allow
JWT = "eyJhbGciOi.eyJzdWIiOi.c2lnbmF0dXJl"  # gitleaks:allow


@pytest.fixture(name="config")
def config_fixture(monkeypatch, tmp_path):
    """Operator additions (one invalid) in a temporary build_stream_config.yml."""
    path = tmp_path / "build_stream_config.yml"
    path.write_text(yaml.safe_dump({"redaction": {
        "additional_secret_key_names": ["vault_pass"],
        "additional_secret_patterns": [
            {"id": "acme-token", "pattern": "acme-[A-Za-z0-9]{16}"},
            {"id": "gitlab-token", "pattern": "Zq9Secret[0-9]{4}"},
        ]}}), encoding="utf-8")
    monkeypatch.setattr(retention_config, "build_stream_config_path", lambda: path)
    logging_utils.get_policy_redaction_service.cache_clear()
    yield path
    logging_utils.get_policy_redaction_service.cache_clear()


@pytest.fixture(name="broken_baseline")
def broken_baseline_fixture(monkeypatch, tmp_path, config):
    """Make the policy loader read an invalid baseline file."""
    broken = tmp_path / "baseline.yml"
    broken.write_text("schema_version: 2\n", encoding="utf-8")
    monkeypatch.setattr(logging_utils, "load_policy", lambda path: load_policy(path, broken))
    return config


@pytest.fixture(name="log_base")
def log_base_fixture(monkeypatch, tmp_path):
    """Send job and event logs to a temporary directory."""
    base = tmp_path / "log"
    monkeypatch.setattr(logging_utils, "_LOG_BASE", base)
    monkeypatch.setattr(logging_utils, "_event_logger", None)
    yield base
    logging_utils.remove_job_logger("job-1")
    events = logging.getLogger("build_stream.events")
    for handler in list(events.handlers):
        handler.close()
        events.removeHandler(handler)


def test_service_applies_operator_additions_and_logs_errors(config, caplog):
    """GIVEN additions with one invalid entry THEN the valid ones apply and one safe error is logged."""
    del config
    with caplog.at_level(logging.ERROR, logger="api.logging_utils"):
        service = dependencies.get_redaction_service()
    assert service is logging_utils.get_policy_redaction_service()
    assert service.redact(f"vault_pass: s3cret {ACME} token=abc123") == (
        "vault_pass: ***REDACTED*** ***REDACTED*** token=***REDACTED***")
    errors = [record.getMessage() for record in caplog.records]
    assert len(errors) == 1 and "gitlab-token" in errors[0] and "Zq9Secret" not in errors[0]


def test_invalid_project_name_falls_back_to_baseline(monkeypatch, caplog):
    """GIVEN an invalid OMNIA_PROJECT_NAME THEN the baseline applies and one safe error is logged."""
    def _invalid_path():
        raise ValueError("OMNIA_PROJECT_NAME is not a valid single-segment name")

    monkeypatch.setattr(retention_config, "build_stream_config_path", _invalid_path)
    logging_utils.get_policy_redaction_service.cache_clear()
    with caplog.at_level(logging.ERROR, logger="api.logging_utils"):
        service = dependencies.get_redaction_service()
    logging_utils.get_policy_redaction_service.cache_clear()
    assert service.redact("token=abc123") == "token=***REDACTED***"
    assert [record.getMessage() for record in caplog.records] == [
        "Invalid OMNIA_PROJECT_NAME; redaction additions ignored"]


def test_broken_baseline_stops_service_construction(broken_baseline):
    """GIVEN an invalid baseline THEN building the service raises."""
    del broken_baseline
    with pytest.raises(RedactionPolicyError):
        dependencies.get_redaction_service()


def test_audit_logs_use_the_policy(config, log_base):
    """GIVEN an operator rule THEN job and event audit logs hold its match and baseline data redacted."""
    del config
    logging_utils.create_job_log_file("job-1")
    message = f"key {ACME} password=hunter2 bearer {JWT}"  # gitleaks:allow
    logging_utils.log_secure_info("info", f"{message} from 10.1.2.3 by a@b.example", job_id="job-1")
    logging_utils.log_auth_info("info", f"client key {ACME} from 10.1.2.3")
    job_text = (log_base / "job-1" / "job-1.log").read_text(encoding="utf-8")
    event_text = (log_base / "events.log").read_text(encoding="utf-8")
    for value in (ACME, "hunter2", JWT, "10.1.2.3", "a@b.example"):
        assert value not in job_text and value not in event_text
    assert "key ***REDACTED*** password=***REDACTED***" in job_text  # gitleaks:allow
    assert "<REDACTED_IP>" in job_text and "<REDACTED_EMAIL>" in job_text
    assert "client key ***REDACTED*** from <REDACTED_IP>" in event_text


def test_broken_baseline_withholds_audit_lines(broken_baseline, log_base):
    """GIVEN the policy cannot be built THEN the audit line is withheld, never written unredacted."""
    del broken_baseline
    logging_utils.create_job_log_file("job-1")
    logging_utils.log_secure_info("info", "password=hunter2", job_id="job-1")  # gitleaks:allow
    text = (log_base / "job-1" / "job-1.log").read_text(encoding="utf-8")
    assert "hunter2" not in text and REDACTION_SUPPRESSED_LINE in text
