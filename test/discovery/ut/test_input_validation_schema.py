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
"""Unit tests for discovery_config.json schema validation."""

# Pytest injects fixtures by reusing fixture function names as test arguments,
# and descriptive test names make per-test docstrings redundant.
# pylint: disable=missing-function-docstring,redefined-outer-name

import copy
import json
import logging
from pathlib import Path

import pytest

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = (
    REPO_ROOT
    / "src/discovery/plugins/module_utils/discovery_validation/schema"
)
LOGGER = logging.getLogger(__name__)


def _load_schema(name):
    """Load a JSON schema file from the schema directory."""
    schema_path = SCHEMA_DIR / name
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _validate(data, schema_name):
    """Validate data against a JSON schema; return list of error strings."""
    if not HAS_JSONSCHEMA:
        pytest.skip("jsonschema not installed")
    schema = _load_schema(schema_name)
    validator = jsonschema.Draft7Validator(schema)
    return [e.message for e in validator.iter_errors(data)]


# ─── Schema file existence ──────────────────────────────────────────────────


class TestDiscoveryConfigSchemaFile:
    """Validate the schema file itself."""

    def test_schema_file_exists(self):
        assert (SCHEMA_DIR / "discovery_config.json").exists()

    def test_schema_is_valid_json(self):
        data = json.loads(
            (SCHEMA_DIR / "discovery_config.json").read_text(encoding="utf-8")
        )
        assert isinstance(data, dict)

    def test_schema_has_draft_declaration(self):
        data = _load_schema("discovery_config.json")
        assert "$schema" in data

    def test_schema_requires_ome_ip(self):
        data = _load_schema("discovery_config.json")
        assert "ome_ip" in data.get("required", [])

    def test_credential_rules_file_exists(self):
        assert (SCHEMA_DIR / "credential_rules.json").exists()

    def test_credential_rules_is_valid_json(self):
        data = json.loads(
            (SCHEMA_DIR / "credential_rules.json").read_text(encoding="utf-8")
        )
        assert isinstance(data, dict)


# ─── discovery_config.json validation ────────────────────────────────────────


@pytest.fixture
def valid_config():
    """Return a minimal valid discovery config."""
    return {
        "ome_ip": "192.168.1.100",
    }


def test_valid_config_passes(valid_config):
    assert not _validate(valid_config, "discovery_config.json")


def test_ome_ip_required():
    errors = _validate({}, "discovery_config.json")
    assert any("ome_ip" in e for e in errors)


@pytest.mark.parametrize(
    "invalid_ip",
    [
        "",
        "not-an-ip",
        "999.999.999.999",
        "192.168.1",
        "abc.def.ghi.jkl",
    ],
)
def test_ome_ip_rejects_invalid_addresses(valid_config, invalid_ip):
    config = copy.deepcopy(valid_config)
    config["ome_ip"] = invalid_ip
    errors = _validate(config, "discovery_config.json")
    assert errors


@pytest.mark.parametrize(
    "valid_ip",
    [
        "10.0.0.1",
        "192.168.1.100",
        "172.16.0.1",
        "255.255.255.255",
    ],
)
def test_ome_ip_accepts_valid_addresses(valid_config, valid_ip):
    config = copy.deepcopy(valid_config)
    config["ome_ip"] = valid_ip
    assert not _validate(config, "discovery_config.json")


def test_ome_ip_rejects_non_string_type(valid_config):
    config = copy.deepcopy(valid_config)
    config["ome_ip"] = 192168
    errors = _validate(config, "discovery_config.json")
    assert any("is not of type" in e for e in errors)


def test_config_allows_additional_properties(valid_config):
    config = copy.deepcopy(valid_config)
    config["custom_field"] = "extra_value"
    assert not _validate(config, "discovery_config.json")


# ─── credential_rules.json validation ───────────────────────────────────────


class TestCredentialRulesSchema:
    """Validate credential rule definitions."""

    def test_ome_username_rule_exists(self):
        rules = json.loads(
            (SCHEMA_DIR / "credential_rules.json").read_text(encoding="utf-8")
        )
        assert "ome_username" in rules

    def test_ome_password_rule_exists(self):
        rules = json.loads(
            (SCHEMA_DIR / "credential_rules.json").read_text(encoding="utf-8")
        )
        assert "ome_password" in rules

    def test_bmc_username_rule_exists(self):
        rules = json.loads(
            (SCHEMA_DIR / "credential_rules.json").read_text(encoding="utf-8")
        )
        assert "bmc_username" in rules

    def test_bmc_password_rule_exists(self):
        rules = json.loads(
            (SCHEMA_DIR / "credential_rules.json").read_text(encoding="utf-8")
        )
        assert "bmc_password" in rules

    def test_provision_password_rule_exists(self):
        rules = json.loads(
            (SCHEMA_DIR / "credential_rules.json").read_text(encoding="utf-8")
        )
        assert "provision_password" in rules

    def test_each_rule_has_min_length(self):
        rules = json.loads(
            (SCHEMA_DIR / "credential_rules.json").read_text(encoding="utf-8")
        )
        for name, rule in rules.items():
            assert "minLength" in rule, (
                f"Credential rule '{name}' missing minLength"
            )

    def test_each_rule_has_description(self):
        rules = json.loads(
            (SCHEMA_DIR / "credential_rules.json").read_text(encoding="utf-8")
        )
        for name, rule in rules.items():
            assert "description" in rule, (
                f"Credential rule '{name}' missing description"
            )
