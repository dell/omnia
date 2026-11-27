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

"""JSON schema (L1) rules for the operator redaction section (ER-BSM-003 FR-3.3)."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

SCHEMA_PATH = (
    Path(__file__).resolve().parents[5] / "src" / "build_stream" / "plugins"
    / "module_utils" / "input_validation" / "schema" / "build_stream_config.json"
)


def _validator() -> Draft7Validator:
    """Return the checked-in BuildStream input-schema validator."""
    return Draft7Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def _document(redaction) -> dict:
    """Return a minimal document with build stream disabled and a redaction section."""
    return {"enable_build_stream": False, "redaction": redaction}


def _pattern(rule_id="acme-token", pattern="acme-[A-Za-z0-9]{16}", **extra) -> dict:
    """Return one operator pattern entry."""
    return {"id": rule_id, "pattern": pattern, **extra}


def _errors(redaction) -> list:
    """Return the schema error messages for a redaction section."""
    return [error.message for error in _validator().iter_errors(_document(redaction))]


@pytest.mark.unit
def test_empty_lists_are_accepted():
    """GIVEN the shipped empty redaction section THEN the schema accepts it."""
    assert _errors({"additional_secret_key_names": [], "additional_secret_patterns": []}) == []


@pytest.mark.unit
def test_limits_are_inclusive():
    """GIVEN 50 names and 50 patterns at the length limits THEN the schema accepts them."""
    names = ["a" + "b" * 39] * 49 + ["Vault.pass-key_1"]
    patterns = [
        _pattern(rule_id="a" + "b" * 40, pattern="p" * 256, description="d" * 200)
        for _ in range(50)
    ]
    assert _errors({"additional_secret_key_names": names,
                    "additional_secret_patterns": patterns}) == []


@pytest.mark.unit
@pytest.mark.parametrize("names", [
    ["x"] * 51,
    ["1leading-digit"],
    ["has space"],
    ["a" * 41],
    [""],
    [7],
])
def test_invalid_key_names_are_rejected(names):
    """GIVEN a key name that breaks the format or limits THEN the schema rejects it."""
    assert _errors({"additional_secret_key_names": names}) != []


@pytest.mark.unit
@pytest.mark.parametrize("entry", [
    _pattern(rule_id="A"),
    _pattern(rule_id="1acme"),
    _pattern(rule_id="a" * 42),
    _pattern(pattern=""),
    _pattern(pattern="p" * 257),
    _pattern(description="d" * 201),
    _pattern(replacement="x"),
    {"id": "acme-token"},
    {"pattern": "acme-[A-Za-z0-9]{16}"},
    "acme-[A-Za-z0-9]{16}",
])
def test_invalid_pattern_entries_are_rejected(entry):
    """GIVEN a pattern entry outside the schema THEN the schema rejects it."""
    assert _errors({"additional_secret_patterns": [entry]}) != []


@pytest.mark.unit
def test_pattern_list_over_limit_is_rejected():
    """GIVEN 51 pattern entries THEN the schema rejects the list."""
    entries = [_pattern(rule_id=f"acme-{index}") for index in range(51)]
    assert _errors({"additional_secret_patterns": entries}) != []


@pytest.mark.unit
@pytest.mark.parametrize("section", [
    {"unknown": []},
    {"additional_secret_key_names": "vault_pass"},
    {"additional_secret_patterns": {"id": "acme-token"}},
])
def test_unknown_or_wrongly_typed_section_keys_are_rejected(section):
    """GIVEN unknown keys or wrong types in the section THEN the schema rejects it."""
    assert _errors(section) != []


@pytest.mark.unit
def test_redaction_section_is_optional():
    """GIVEN a document without the section THEN the schema accepts it."""
    assert list(_validator().iter_errors({"enable_build_stream": False})) == []
