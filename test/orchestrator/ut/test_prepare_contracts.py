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

"""Fail-closed unit contracts for Orchestrator prepare verification."""

from types import SimpleNamespace

import pytest
from library.functions import external_ldap_func as external_ldap
from library.functions import openchami_prepare_func as openchami
from library.functions import openldap_prepare_func as openldap
from library.functions import postgres_prepare_func as postgres


def _result(rc=0, stdout="", stderr=""):
    return SimpleNamespace(rc=rc, stdout=stdout, stderr=stderr)


@pytest.mark.parametrize(
    ("target_state", "target_rc"),
    [("", 1), ("exited", 0)],
)
def test_required_container_absent_or_stopped_fails(
    monkeypatch, target_state, target_rc
):
    """ORCH_UT_014: Every required OpenCHAMI container must be running."""
    target = openchami.OPENCHAMI_CONTAINERS[0]

    def run_on_host(_host, _command, container):
        if container == target:
            return _result(rc=target_rc, stdout=target_state)
        return _result(stdout="running")

    monkeypatch.setattr(openchami, "run_on_host", run_on_host)
    verification = openchami.check_prepare_openchami_containers(object())

    assert not verification["success"]
    assert target in verification["error"]


@pytest.mark.parametrize("target_state", ["inactive", "unknown"])
def test_required_service_absent_or_inactive_fails(monkeypatch, target_state):
    """ORCH_UT_015: Every required OpenCHAMI systemd unit must be active."""
    target = openchami.OPENCHAMI_ACTIVE_UNITS[0]

    def run_on_host(_host, command, unit):
        if command == openchami.PREPARE_COMMANDS["unit_result"]:
            return _result(stdout="success")
        if unit == target:
            return _result(rc=1, stdout=target_state)
        return _result(stdout="active")

    monkeypatch.setattr(openchami, "run_on_host", run_on_host)
    verification = openchami.check_prepare_openchami_services(object())

    assert not verification["success"]
    assert target in verification["error"]


@pytest.mark.parametrize("initialization_state", ["unavailable", "failed"])
def test_missing_or_unsuccessful_smd_initialization_fails(
    monkeypatch, initialization_state
):
    """ORCH_UT_016: Missing or failed SMD initialization cannot pass."""

    def run_on_host(_host, command, _unit):
        if command == openchami.PREPARE_COMMANDS["unit_result"]:
            return _result(
                rc=0 if initialization_state == "failed" else 1,
                stdout=initialization_state,
            )
        return _result(stdout="active")

    monkeypatch.setattr(openchami, "run_on_host", run_on_host)
    verification = openchami.check_prepare_openchami_services(object())

    assert not verification["success"]
    assert openchami.OPENCHAMI_INITIALIZATION_UNIT in verification["error"]


@pytest.mark.parametrize(
    "metadata_result",
    ["", "PROBE|2|transport|7\n"],
)
def test_unavailable_required_api_fails(monkeypatch, metadata_result):
    """ORCH_UT_017: A missing required OpenCHAMI API result is a failure."""
    monkeypatch.setattr(
        openchami,
        "_openchami_base_url",
        lambda _host: "https://oim.example.test:8443",
    )
    monkeypatch.setattr(
        openchami,
        "run_on_host",
        lambda *_args: _result(
            rc=0,
            stdout=(
                "TOKEN|generated\n"
                "PROBE|0|reachable|200\n"
                "PROBE|1|reachable|200\n"
                f"{metadata_result}"
            ),
        ),
    )

    verification = openchami.check_prepare_openchami_apis(object())

    assert not verification["success"]
    assert "Metadata Service:" in verification["error"]


@pytest.mark.parametrize(
    ("is_file", "size"),
    [(False, 0), (True, 0)],
)
def test_missing_or_empty_postgresql_init_script_fails(monkeypatch, is_file, size):
    """ORCH_UT_018: PostgreSQL initialization needs a nonempty script."""
    monkeypatch.setattr(openchami, "OPENCHAMI_PACKAGES", ())
    monkeypatch.setattr(openchami, "OPENCHAMI_CONFIG_ARTIFACTS", ())
    host = SimpleNamespace(
        file=lambda _path: SimpleNamespace(is_file=is_file, size=size)
    )

    verification = openchami.check_prepare_openchami_artifacts(host)

    assert not verification["success"]
    assert openchami.POSTGRES_INIT_SCRIPT in verification["error"]


def test_postgresql_readiness_requires_every_contract(monkeypatch):
    """ORCH_UT_019: Partial PostgreSQL output cannot report readiness."""
    monkeypatch.setattr(
        postgres,
        "run_on_host",
        lambda *_args: _result(
            rc=24,
            stdout="READY|ready\nDATABASE|present\nROLE|missing\n",
        ),
    )

    verification = postgres.check_prepare_postgresql_readiness(object())

    assert not verification["success"]
    assert "Role smd-user=missing" in verification["error"]
    assert "Read-only query on hmsds=not checked" in verification["error"]


def test_postgresql_readiness_accepts_complete_read_only_probe(monkeypatch):
    """ORCH_UT_020: Complete PostgreSQL readiness evidence passes."""
    monkeypatch.setattr(
        postgres,
        "run_on_host",
        lambda *_args: _result(
            stdout=("READY|ready\nDATABASE|present\nROLE|present\nQUERY|passed\n")
        ),
    )

    verification = postgres.check_prepare_postgresql_readiness(object())

    assert verification["success"]
    assert not verification["skipped"]


def test_explicitly_disabled_optional_openldap_skips(monkeypatch):
    """ORCH_UT_021: Catalog-disabled OpenLDAP is an intentional skip."""
    monkeypatch.setattr(openldap, "_openldap_enabled", lambda _host: False)

    verification = openldap.check_prepare_openldap_runtime(object())

    assert verification["success"]
    assert verification["skipped"]


def test_enabled_optional_openldap_missing_runtime_fails(monkeypatch):
    """ORCH_UT_022: Enabled OpenLDAP cannot skip a missing runtime."""
    monkeypatch.setattr(openldap, "_openldap_enabled", lambda _host: True)
    monkeypatch.setattr(
        openldap,
        "run_on_host",
        lambda *_args: _result(rc=1),
    )

    verification = openldap.check_prepare_openldap_runtime(object())

    assert not verification["success"]
    assert not verification["skipped"]
    assert "unavailable" in verification["error"]


@pytest.mark.parametrize(
    ("state", "error_fragment"),
    [
        (None, "Required YAML file is missing"),
        ({}, "boolean openldap_support"),
        ({"openldap_support": "true"}, "boolean openldap_support"),
    ],
)
def test_missing_or_malformed_optional_feature_state_fails(
    monkeypatch, state, error_fragment
):
    """ORCH_UT_023: Invalid optional-feature state fails instead of skipping."""
    monkeypatch.setattr(
        openldap,
        "resolve_target_output_project_path",
        lambda _host: "/omnia/orchestrator/output/project",
    )

    def read_state(_host, _path):
        if state is None:
            raise ValueError("Required YAML file is missing: orchestrator_state.yml")
        return state

    monkeypatch.setattr(openldap, "read_yaml_mapping", read_state)

    verification = openldap.check_prepare_openldap_runtime(object())

    assert not verification["success"]
    assert not verification["skipped"]
    assert error_fragment in verification["error"]


def test_external_ldap_validation_defaults_to_disabled():
    """ORCH_UT_026: External LDAP validation is explicitly opt-in."""
    settings = external_ldap.load_external_ldap_settings({})

    assert not settings["validation_enabled"]
    assert not settings["configuration_enabled"]


def test_external_ldap_validation_requires_complete_endpoint():
    """ORCH_UT_027: Enabled validation fails on incomplete endpoint input."""
    with pytest.raises(ValueError, match="external_ldap_server_ip"):
        external_ldap.load_external_ldap_settings({"validate_external_ldap": True})


def test_external_ldap_validation_opt_out_skips_before_mutation(monkeypatch):
    """ORCH_UT_028: Disabled validation cannot reconcile the LDAP proxy."""
    monkeypatch.setattr(openldap, "_openldap_enabled", lambda _host: True)
    monkeypatch.setattr(
        openldap,
        "load_external_ldap_settings",
        lambda: {
            "validation_enabled": False,
            "configuration_enabled": True,
        },
    )

    def unexpected_reconciliation(_host):
        raise AssertionError("LDAP reconciliation must not run")

    monkeypatch.setattr(
        openldap,
        "configure_external_ldap_proxy",
        unexpected_reconciliation,
    )

    verification = openldap.reconcile_prepare_external_ldap_proxy(object())

    assert verification["success"]
    assert verification["skipped"]
    assert dict(verification["fields"])["validate_external_ldap"] is False


def test_external_ldap_validation_does_not_hide_existing_proxy_failure(monkeypatch):
    """ORCH_UT_029: Validation-only mode reports a deployed proxy failure."""
    monkeypatch.setattr(openldap, "_openldap_enabled", lambda _host: True)
    monkeypatch.setattr(
        openldap,
        "load_external_ldap_settings",
        lambda: {
            "validation_enabled": True,
            "configuration_enabled": False,
        },
    )
    monkeypatch.setattr(
        openldap,
        "configure_external_ldap_proxy",
        lambda _host: {
            "success": True,
            "changed": False,
            "skipped": True,
            "details": "configure_external_ldap is false",
            "error": "",
        },
    )
    monkeypatch.setattr(
        openldap,
        "check_prepare_external_ldap_proxy",
        lambda _host: {
            "success": False,
            "skipped": False,
            "details": "External LDAP proxy verification failed",
            "fields": [],
            "error": "deployed proxy does not match",
        },
    )

    verification = openldap.reconcile_prepare_external_ldap_proxy(object())

    assert not verification["success"]
    assert not verification["skipped"]
    assert verification["error"] == "deployed proxy does not match"
