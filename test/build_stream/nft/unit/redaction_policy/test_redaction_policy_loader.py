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

"""Loader behaviour: operator additions, operator errors and baseline failures (TC-UT-018)."""

from pathlib import Path

import pytest
import yaml

from core.logs.redaction import RedactionService
from core.logs.redaction_policy import (
    BASELINE_POLICY_PATH,
    RedactionPolicyError,
    load_baseline,
    load_policy,
)

pytestmark = pytest.mark.unit

ACME = "acme-[A-Za-z0-9]{16}"
ACME_SECRET = "acme-0123456789abcdef"  # gitleaks:allow


def _config(tmp_path: Path, document) -> Path:
    """Write a build_stream_config.yml fixture (a string is written verbatim)."""
    path = tmp_path / "build_stream_config.yml"
    path.write_text(document if isinstance(document, str) else yaml.safe_dump(document),
                    encoding="utf-8")
    return path


def _redact(policy, text: str) -> str:
    """Apply the policy's Tier 1 rules to one line."""
    return RedactionService(policy.secret_rules, policy.identifier_rules).redact(text)


def _section(**section) -> dict:
    """Return a configuration document holding only the redaction section."""
    return {"redaction": section}


def _baseline(tmp_path: Path, mutate) -> Path:
    """Write a mutated copy of the shipped baseline and return its path."""
    with BASELINE_POLICY_PATH.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    mutate(document)
    path = tmp_path / "baseline.yml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


@pytest.mark.parametrize("content", [None, "", {"build_stream": {"enabled": True}},
                                     {"redaction": {"additional_secret_key_names": [],
                                                    "additional_secret_patterns": []}}])
def test_absent_or_empty_operator_section_gives_baseline_only(tmp_path, content):
    """GIVEN no operator additions THEN the policy is the baseline with no errors."""
    path = tmp_path / "absent.yml" if content is None else _config(tmp_path, content)
    policy = load_policy(path)
    assert policy.operator_errors == []
    assert _redact(policy, "vault_pass: s3cret") == "vault_pass: s3cret"
    assert len(policy.secret_rules) == len(load_baseline().secret_rules)


def test_operator_key_name_and_pattern_are_applied_after_baseline(tmp_path):
    """GIVEN a key name and a pattern THEN both are redacted, the pattern after the baseline."""
    config = _config(tmp_path, _section(additional_secret_key_names=["vault.pass"],
                                        additional_secret_patterns=[
                                            {"id": "acme-token", "pattern": ACME}]))
    policy = load_policy(config)
    assert policy.operator_errors == []
    assert _redact(policy, "vault.pass: s3cret") == "vault.pass: ***REDACTED***"
    assert _redact(policy, 'vault.pass = "s3cret"') == 'vault.pass = "***REDACTED***"'
    assert _redact(policy, "vaultXpass: s3cret") == "vaultXpass: s3cret"
    assert _redact(policy, f"acme {ACME_SECRET} glpat-abcdefghijk12345") == (
        "acme ***REDACTED*** ***REDACTED***")
    assert policy.secret_rules[-1][0].pattern == ACME


def test_operator_key_names_dedupe_case_insensitively(tmp_path):
    """GIVEN key names differing only by case THEN they are accepted without errors."""
    policy = load_policy(_config(tmp_path, _section(
        additional_secret_key_names=["Vault_Pass", "vault_pass", "PASSWORD"])))
    assert policy.operator_errors == []
    assert _redact(policy, "VAULT_PASS: s3cret") == "VAULT_PASS: ***REDACTED***"


@pytest.mark.parametrize("entries, message_parts, leaked", [
    ([{"id": "gitlab-token", "pattern": "Zq9Secret[0-9]{4}"}], ["gitlab-token"], "Zq9Secret"),
    ([{"id": "key-value", "pattern": "Zq9Secret[0-9]{4}"}], ["key-value"], "Zq9Secret"),
    ([{"id": "zq-leak", "pattern": "Zq9Secret.*"}], ["zq-leak", "unbounded-quantifier"],
     "Zq9Secret"),
    ([{"id": "Bad_Id", "pattern": "Zq9Secret[0-9]{4}"}], ["[0]"], "Zq9Secret"),
    ([{"id": "acme-token", "pattern": ACME, "replacement": "x"}], ["[0]"], None),
    ([{"id": "acme-token", "pattern": ACME, "description": "d" * 201}], ["[0]"], None),
    ([{"id": "acme-token", "pattern": 12}], ["[0]"], None),
])
def test_invalid_pattern_entries_are_skipped_and_reported_without_pattern_text(
        tmp_path, entries, message_parts, leaked):
    """GIVEN an invalid entry THEN it is skipped and the message names its id or index only."""
    policy = load_policy(_config(tmp_path, _section(additional_secret_patterns=entries)))
    assert policy.operator_errors
    for part in message_parts:
        assert any(part in message for message in policy.operator_errors)
    if leaked:
        assert all(leaked not in message for message in policy.operator_errors)
    assert _redact(policy, "password: s3cret") == "password: ***REDACTED***"  # gitleaks:allow


def test_valid_entry_is_kept_when_another_is_invalid(tmp_path):
    """GIVEN one invalid and one valid entry THEN only the valid one is applied."""
    policy = load_policy(_config(tmp_path, _section(additional_secret_patterns=[
        {"id": "bad-one", "pattern": "(unclosed"},
        {"id": "acme-token", "pattern": ACME}])))
    assert len(policy.operator_errors) == 1
    assert _redact(policy, ACME_SECRET) == "***REDACTED***"


def test_duplicate_id_keeps_first_entry(tmp_path):
    """GIVEN two entries with one id THEN the first is applied and the second is reported."""
    policy = load_policy(_config(tmp_path, _section(additional_secret_patterns=[
        {"id": "acme-token", "pattern": ACME}, {"id": "acme-token", "pattern": "other-[0-9]{4}"}])))
    assert len(policy.operator_errors) == 1
    assert policy.secret_rules[-1][0].pattern == ACME


@pytest.mark.parametrize("section, expected_key_message", [
    (_section(additional_secret_key_names=["bad name", "vault_pass"]), "[0]"),
    (_section(additional_secret_key_names=[f"name{index}" for index in range(51)]), "at most 50"),
    (_section(additional_secret_patterns=[{"id": f"acme-{i}", "pattern": f"zq{i}[0-9]"}
                                          for i in range(51)]), "at most 50"),
    (_section(additional_secret_key_names="vault"), "must be a list"),
    ({"redaction": "a string"}, "invalid"),
    ({"redaction": ["a list"]}, "invalid"),
    (_section(unknown=["x"]), "invalid"),
])
def test_invalid_operator_section_is_reported(tmp_path, section, expected_key_message):
    """GIVEN an invalid operator section THEN it is ignored or skipped and reported."""
    policy = load_policy(_config(tmp_path, section))
    assert any(expected_key_message in message for message in policy.operator_errors)
    assert _redact(policy, "password: s3cret") == "password: ***REDACTED***"  # gitleaks:allow


def test_valid_key_name_survives_when_another_is_invalid(tmp_path):
    """GIVEN a malformed key name next to a valid one THEN the valid name still applies."""
    policy = load_policy(_config(tmp_path, _section(
        additional_secret_key_names=["bad name", "vault_pass"])))
    assert _redact(policy, "vault_pass: s3cret") == "vault_pass: ***REDACTED***"


@pytest.mark.parametrize("text", ["redaction: [unclosed, Zq9Secret\n", "- a\n- b\n"])
def test_unparseable_or_non_mapping_config_is_reported_without_content(tmp_path, text):
    """GIVEN invalid YAML or a non-mapping document THEN one error is reported, no content."""
    policy = load_policy(_config(tmp_path, text))
    assert len(policy.operator_errors) == 1
    assert "Zq9Secret" not in policy.operator_errors[0]
    assert _redact(policy, "password: s3cret") == "password: ***REDACTED***"  # gitleaks:allow


def test_unreadable_config_is_reported(tmp_path):
    """GIVEN a config path that cannot be read THEN the baseline applies and one error is reported."""
    policy = load_policy(tmp_path)
    assert len(policy.operator_errors) == 1
    assert _redact(policy, "password: s3cret") == "password: ***REDACTED***"  # gitleaks:allow


@pytest.mark.parametrize("mutate", [
    lambda doc: doc.update(schema_version=2),
    lambda doc: doc.update(schema_version=True),
    lambda doc: doc.update(schema_version="1"),
    lambda doc: doc.update(extra=1),
    lambda doc: doc.update(secret_key_names=["bad name"]),
    lambda doc: doc["secret_patterns"][0].update(pattern="Zq9.*"),
    lambda doc: doc["secret_patterns"][2].update(replacement="\\2***"),
    lambda doc: doc["secret_patterns"][0].update(replacement="a\\nb"),
    lambda doc: doc["identifier_patterns"][0].update(id="jwt"),
])
def test_invalid_baseline_raises(tmp_path, mutate):
    """GIVEN an invalid baseline THEN loading raises so no service starts with fewer rules."""
    with pytest.raises(RedactionPolicyError):
        load_policy(None, _baseline(tmp_path, mutate))


def test_missing_and_unparseable_baseline_raise(tmp_path):
    """GIVEN a missing or non-YAML baseline THEN loading raises."""
    bad = tmp_path / "bad.yml"
    bad.write_text("schema_version: [unclosed\n", encoding="utf-8")
    with pytest.raises(RedactionPolicyError):
        load_policy(None, tmp_path / "absent.yml")
    with pytest.raises(RedactionPolicyError):
        load_baseline(bad)


def test_baseline_error_is_not_masked_by_operator_section(tmp_path):
    """GIVEN a broken baseline and a valid operator section THEN loading still raises."""
    path = _baseline(tmp_path, lambda doc: doc["secret_patterns"][0].update(pattern="Zq9.*"))
    with pytest.raises(RedactionPolicyError):
        load_policy(_config(tmp_path, _section(additional_secret_key_names=["x"])), path)
