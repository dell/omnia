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

"""Semantic checks (L2) for the operator redaction section (ER-BSM-003 FR-3.3)."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

VALIDATION_DIR = (
    Path(__file__).resolve().parents[5] / "src" / "build_stream" / "plugins"
    / "module_utils" / "input_validation"
)
UNSAFE_PATTERN = "Zq9Secret.*"


def _load_module(name: str, path: Path):
    """Load a module from a file under a unique name."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="validator")
def fixture_validator(monkeypatch):
    """Load the L2 validator with the Ansible module_utils import path stubbed."""
    messages = _load_module(
        "bsm_messages_redaction", VALIDATION_DIR / "messages" / "build_stream_messages.py"
    )
    check = _load_module(
        "bsm_redaction_check", VALIDATION_DIR / "validators" / "redaction_pattern_check.py"
    )
    packages = {
        "ansible.module_utils.input_validation": types.ModuleType("input_validation"),
        "ansible.module_utils.input_validation.messages": types.ModuleType("messages"),
        "ansible.module_utils.input_validation.validators": types.ModuleType("validators"),
    }
    packages["ansible.module_utils.input_validation.messages"].build_stream_messages = messages
    packages["ansible.module_utils.input_validation.validators"].redaction_pattern_check = check
    for name, module in packages.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setitem(
        sys.modules, "ansible.module_utils.input_validation.validators.redaction_pattern_check",
        check,
    )
    return _load_module(
        "bsm_validator_redaction",
        VALIDATION_DIR / "validators" / "build_stream_config_validator.py",
    )


def _config(redaction=None, **extra) -> dict:
    """Return an enabled, otherwise valid configuration with an optional redaction section."""
    config = {
        "enable_build_stream": True,
        "build_stream_host_ip": "10.0.0.1",
        "build_stream_port": 8010,
        "gitlab_mode": "hosted",
        "gitlab_host": "10.0.0.2",
        **extra,
    }
    if redaction is not None:
        config["redaction"] = redaction
    return config


def _pattern(rule_id, pattern=UNSAFE_PATTERN):
    """Return one operator pattern entry."""
    return {"id": rule_id, "pattern": pattern}


def test_valid_additions_produce_no_errors(validator):
    """GIVEN safe additions THEN the validator reports nothing."""
    config = _config({
        "additional_secret_key_names": ["vault_pass"],
        "additional_secret_patterns": [_pattern("acme-token", "acme-[A-Za-z0-9]{16}")],
    })
    assert validator.validate(config) == []


def test_empty_redaction_section_produces_no_errors(validator):
    """GIVEN the shipped empty section THEN the validator reports nothing."""
    assert validator.validate(_config({
        "additional_secret_key_names": [], "additional_secret_patterns": []})) == []


def test_missing_redaction_section_produces_no_errors(validator):
    """GIVEN no redaction section THEN the validator reports nothing."""
    assert validator.validate(_config()) == []


def test_disabled_build_stream_skips_redaction_checks(validator):
    """GIVEN build stream disabled THEN an unsafe addition is not checked."""
    config = _config({"additional_secret_patterns": [_pattern("gitlab-token")]})
    config["enable_build_stream"] = False
    assert validator.validate(config) == []


@pytest.mark.parametrize("pattern, reason", [
    (UNSAFE_PATTERN, "unbounded-quantifier"),
    (r"(a)\1", "group-reference"),
    ("(unclosed", "does-not-compile"),
    (r"(?:\d{1,3}\.){3}\d", "nested-quantifier"),
])
def test_unsafe_pattern_error_names_id_and_reason_only(validator, pattern, reason):
    """GIVEN an unsafe pattern THEN the error names the id and reason, never the pattern."""
    errors = validator.validate(_config({"additional_secret_patterns": [
        _pattern("zq-leak", pattern)]}))
    assert len(errors) == 1
    assert "zq-leak" in errors[0]
    assert reason in errors[0]
    assert pattern not in errors[0]


def test_reserved_baseline_id_is_rejected(validator):
    """GIVEN a pattern id that reuses a baseline id THEN validation names it."""
    errors = validator.validate(_config({"additional_secret_patterns": [
        _pattern("gitlab-token", "Zq9Secret[0-9]{4}")]}))
    assert len(errors) == 1
    assert "gitlab-token" in errors[0]
    assert "Zq9Secret" not in errors[0]


@pytest.mark.parametrize("rule_id", ["private-key", "key-value", "ipv4", "email"])
def test_built_in_and_identifier_ids_are_reserved(validator, rule_id):
    """GIVEN the id of any built-in or identifier rule THEN the id is rejected."""
    errors = validator.validate(_config({"additional_secret_patterns": [
        _pattern(rule_id, "Zq9Secret[0-9]{4}")]}))
    assert len(errors) == 1
    assert rule_id in errors[0]


def test_duplicate_operator_id_is_rejected(validator):
    """GIVEN two patterns with the same id THEN the second is reported by id."""
    errors = validator.validate(_config({"additional_secret_patterns": [
        _pattern("acme-token", "acme-[A-Za-z0-9]{16}"),
        _pattern("acme-token", "other-[0-9]{4}"),
    ]}))
    assert len(errors) == 1
    assert "acme-token" in errors[0]
    assert "other-" not in errors[0]


def test_invalid_pattern_id_is_reported_by_index(validator):
    """GIVEN an id that is not well formed THEN the error names the entry index only."""
    errors = validator.validate(_config({"additional_secret_patterns": [
        _pattern("Bad_Id", "Zq9Secret[0-9]{4}")]}))
    assert len(errors) == 1
    assert "[0]" in errors[0]
    assert "Bad_Id" not in errors[0]
    assert "Zq9Secret" not in errors[0]


def test_invalid_key_name_is_reported_by_index(validator):
    """GIVEN a malformed key name THEN the error names the index, not the name."""
    errors = validator.validate(_config({"additional_secret_key_names": [
        "vault_pass", "bad name"]}))
    assert len(errors) == 1
    assert "[1]" in errors[0]
    assert "bad name" not in errors[0]


def test_each_offending_entry_is_reported(validator):
    """GIVEN several unsafe entries THEN each one gets its own error."""
    errors = validator.validate(_config({"additional_secret_patterns": [
        _pattern("first-one", UNSAFE_PATTERN),
        _pattern("second-one", r"(a)\1"),
    ]}))
    assert len(errors) == 2
    assert "first-one" in errors[0]
    assert "second-one" in errors[1]


def test_non_mapping_section_is_left_to_schema(validator):
    """GIVEN a non-mapping section THEN the semantic check does not raise."""
    assert validator.validate(_config(["not", "a", "mapping"])) == []
