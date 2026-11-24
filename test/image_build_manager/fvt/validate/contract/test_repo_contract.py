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

"""
Image Build Validate — External repo_manager Contract Verification.

Validates that image_build_manager correctly consumes repo_status.yml when
the repo_manager output is provided by an external source (a different OIM,
a CI artifact, an operator-supplied file, or the internet fixture).  The
consumer must work and pass regardless of which producer-owned metadata is
present, which optional sections exist, or which extra fields the producer
adds in future versions.

Contract pipeline under test:
  1. JSON Schema validation (repo_status.json)
  2. Semantic validation (repo_status_validator.validate)
  3. parse_repo_status — extracts consumer-required facts

**Data-source breakdown (20 verification tests):**

==========  =================  ==========================================
Category    Tests              Data source
==========  =================  ==========================================
Synthetic   V005-V017, V020,   ``minimal_external_status()`` — hand-built
fixtures    V021, V023, V024   dicts in ``contract_func.py``
Bundled     V018, V019         ``load_sample_status()`` reading
samples                        ``src/.../samples/repo_manager_output/``
Live file   **V022**           ``live_status_path()`` → real repo_status
==========  =================  ==========================================

V022 is the only verification test that requires the live file.  When
the file is absent, V022 **skips** by default (safe for dev-box runs)
or **fails** when ``REQUIRE_LIVE_REPO_STATUS=1`` is set (CI / nightly).

A report showing "20 passed, 0 skipped" confirms the live-file path was
exercised.  A report with skips means the live-file tests were not run —
the terminal summary surfaces this explicitly.
"""

import os

import pytest
import yaml

from library.functions import TestLogger, load_test_config
from library.functions.contract_func import (
    validate_repo_contract,
    parse_repo_status_external,
    minimal_external_status,
    write_status_fixture,
    load_sample_status,
    live_status_path,
    local_addresses,
    verify_external_source,
)
from library.vars import TEST_CASES as TC
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT

_REQUIRE_LIVE = os.environ.get("REQUIRE_LIVE_REPO_STATUS", "") == "1"


# =========================================================================
# Contract theme: external repo_manager output consumed by image_build_manager
# =========================================================================


@pytest.mark.sanity
@pytest.mark.order(10)
def test_external_contract_minimal(tmp_path):
    """Verify minimal external repo_status.yml passes full contract."""
    tc = TC["external_contract_minimal"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status()
    path = write_status_fixture(tmp_path, data)

    result = validate_repo_contract(data)
    if not result["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(errors=result["errors"])

    parse = parse_repo_status_external(path)
    if not parse["success"]:
        tl.failed(LOG["contract_parse_failed"], parse["details"])
        assert False, ASSERT["contract_parse_failed"].format(error=parse["error"])

    r = parse["result"]
    tl.passed(LOG["contract_validation_ok"], result["details"])
    assert r["cluster_os_type"] == "rhel"
    assert r["cluster_os_versions"] == ["10.0"]
    assert r["repo_port"] == 443
    assert len(r["repo_manager_repos_x86_64"]) == 1


@pytest.mark.sanity
@pytest.mark.order(11)
def test_external_contract_multi_version(tmp_path):
    """Verify external status with two OS versions parses correctly."""
    tc = TC["external_contract_multi_version"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status(repositories={
        "10.0": {"x86_64": {
            "baseos": {"url": "https://ext.example.com/10.0/baseos/"},
            "appstream": {"url": "https://ext.example.com/10.0/appstream/"},
        }},
        "10.2": {"x86_64": {
            "baseos": {"url": "https://ext.example.com/10.2/baseos/"},
        }},
    })
    path = write_status_fixture(tmp_path, data)

    result = validate_repo_contract(data)
    parse = parse_repo_status_external(path)

    if not result["success"] or not parse["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(
            errors=result.get("errors") or parse.get("error"))

    r = parse["result"]
    tl.passed(LOG["contract_validation_ok"], result["details"])
    assert r["cluster_os_versions"] == ["10.0", "10.2"]
    names = {repo["name"] for repo in r["repo_manager_repos_x86_64"]}
    assert "10_0_baseos" in names
    assert "10_2_baseos" in names


@pytest.mark.functional
@pytest.mark.order(12)
def test_external_contract_aarch64_only(tmp_path):
    """Verify external status with aarch64-only repos is valid."""
    tc = TC["external_contract_aarch64_only"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status(repositories={
        "10.0": {"aarch64": {
            "baseos": {"url": "https://ext.example.com/aarch64/baseos/"},
        }},
    })
    path = write_status_fixture(tmp_path, data)

    result = validate_repo_contract(data)
    parse = parse_repo_status_external(path)

    if not result["success"] or not parse["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(
            errors=result.get("errors") or parse.get("error"))

    r = parse["result"]
    tl.passed(LOG["contract_validation_ok"], result["details"])
    assert len(r["repo_manager_repos_x86_64"]) == 0
    assert len(r["repo_manager_repos_aarch64"]) == 1


@pytest.mark.sanity
@pytest.mark.order(13)
def test_external_contract_custom_port(tmp_path):
    """Verify explicit repo_manager.port propagates to consumer."""
    tc = TC["external_contract_custom_port"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status()
    data["repo_manager"] = {"port": 8443}
    path = write_status_fixture(tmp_path, data)

    result = validate_repo_contract(data)
    parse = parse_repo_status_external(path)

    if not result["success"] or not parse["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(
            errors=result.get("errors") or parse.get("error"))

    tl.passed(LOG["contract_port_ok"].format(port=8443), result["details"])
    assert parse["result"]["repo_port"] == 8443


@pytest.mark.functional
@pytest.mark.order(14)
def test_external_contract_url_port(tmp_path):
    """Verify port derived from URL when repo_manager section absent."""
    tc = TC["external_contract_url_port"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status(repositories={
        "10.0": {"x86_64": {
            "baseos": {"url": "https://repo.example.com:9443/baseos/"},
        }},
    })
    path = write_status_fixture(tmp_path, data)

    result = validate_repo_contract(data)
    parse = parse_repo_status_external(path)

    if not result["success"] or not parse["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(
            errors=result.get("errors") or parse.get("error"))

    tl.passed(LOG["contract_port_ok"].format(port=9443), result["details"])
    assert parse["result"]["repo_port"] == 9443


@pytest.mark.sanity
@pytest.mark.order(15)
def test_external_contract_cert_path(tmp_path):
    """Verify certificate metadata propagates to consumer."""
    tc = TC["external_contract_cert_path"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status()
    data["repo_manager"] = {
        "port": 2225,
        "certificates": {
            "server_crt": "/external/certs/ca-bundle.crt",
            "certs_dir": "/external/certs",
        },
    }
    path = write_status_fixture(tmp_path, data)

    result = validate_repo_contract(data)
    parse = parse_repo_status_external(path)

    if not result["success"] or not parse["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(
            errors=result.get("errors") or parse.get("error"))

    r = parse["result"]
    tl.passed(LOG["contract_cert_ok"], result["details"])
    assert r["repo_cert_path"] == "/external/certs/ca-bundle.crt"
    assert r["repo_port"] == 2225


@pytest.mark.functional
@pytest.mark.order(16)
def test_external_contract_empty_cert(tmp_path):
    """Verify internet source with empty cert returns empty string."""
    tc = TC["external_contract_empty_cert"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status()
    data["repo_manager"] = {
        "port": "",
        "certificates": {"server_crt": "", "certs_dir": ""},
    }
    path = write_status_fixture(tmp_path, data)

    result = validate_repo_contract(data)
    parse = parse_repo_status_external(path)

    if not result["success"] or not parse["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(
            errors=result.get("errors") or parse.get("error"))

    tl.passed(LOG["contract_validation_ok"], result["details"])
    assert parse["result"]["repo_cert_path"] == ""


@pytest.mark.functional
@pytest.mark.order(17)
def test_external_contract_producer_metadata_ignored(tmp_path):
    """Verify producer-owned fields are ignored by consumer."""
    tc = TC["external_contract_producer_ignored"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status()
    data["execution_contexts"] = [
        {"context_id": "ext", "os_type": "rhel", "os_version": "10.0",
         "architectures": ["x86_64"]},
    ]
    data["overall_status_by_version"] = {"10.0": "success"}
    data["repo_config"] = "full"
    data["file_repos"] = {"x86_64": {}}
    data["registries"] = {}
    data["future_producer_field"] = {"layout": "v3"}
    path = write_status_fixture(tmp_path, data)

    result = validate_repo_contract(data)
    parse = parse_repo_status_external(path)

    if not result["success"] or not parse["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(
            errors=result.get("errors") or parse.get("error"))

    tl.passed(LOG["contract_producer_ignored_ok"], result["details"])
    assert parse["result"]["cluster_os_type"] == "rhel"
    assert parse["result"]["cluster_os_versions"] == ["10.0"]


@pytest.mark.functional
@pytest.mark.order(18)
def test_external_contract_priority(tmp_path):
    """Verify priority values propagate from external source."""
    tc = TC["external_contract_priority"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status(repositories={
        "10.0": {"x86_64": {
            "baseos": {"url": "https://ext.example.com/baseos/", "priority": 50},
            "custom": {"url": "https://ext.example.com/custom/", "priority": 100},
        }},
    })
    path = write_status_fixture(tmp_path, data)

    result = validate_repo_contract(data)
    parse = parse_repo_status_external(path)

    if not result["success"] or not parse["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(
            errors=result.get("errors") or parse.get("error"))

    repos = {r["name"]: r for r in parse["result"]["repo_manager_repos_x86_64"]}
    tl.passed(LOG["contract_validation_ok"], result["details"])
    assert repos["10_0_baseos"].get("priority") == "50"
    assert repos["10_0_custom"].get("priority") == "100"


@pytest.mark.sanity
@pytest.mark.order(19)
def test_external_contract_failed_status_rejected():
    """Verify external status with overall_status != success is rejected."""
    tc = TC["external_contract_failed_rejected"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status(overall_status="failed")

    result = validate_repo_contract(data)

    if result["success"]:
        tl.failed(LOG["contract_rejection_expected"])
        assert False, ASSERT["contract_rejection_expected"]

    tl.passed(LOG["contract_rejected_ok"], result["details"])
    assert any("success" in e for e in result["errors"])


@pytest.mark.sanity
@pytest.mark.order(20)
def test_external_contract_missing_repos_rejected():
    """Verify external status without repositories is rejected."""
    tc = TC["external_contract_missing_repos"]
    tl = TestLogger(tc["title"], tc["id"])
    data = {"overall_status": "success", "cluster_os_type": "rhel"}

    result = validate_repo_contract(data)

    if result["success"]:
        tl.failed(LOG["contract_rejection_expected"])
        assert False, ASSERT["contract_rejection_expected"]

    tl.passed(LOG["contract_rejected_ok"], result["details"])
    assert any("repositories" in e for e in result["errors"])


@pytest.mark.functional
@pytest.mark.order(21)
def test_external_contract_empty_repos_rejected():
    """Verify external status with empty repositories is rejected."""
    tc = TC["external_contract_empty_repos"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status(repositories={})

    result = validate_repo_contract(data)

    if result["success"]:
        tl.failed(LOG["contract_rejection_expected"])
        assert False, ASSERT["contract_rejection_expected"]

    tl.passed(LOG["contract_rejected_ok"], result["details"])


@pytest.mark.functional
@pytest.mark.order(22)
def test_external_contract_mixed_arch(tmp_path):
    """Verify mixed x86_64 + aarch64 builds separate repo lists."""
    tc = TC["external_contract_mixed_arch"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status(repositories={
        "10.0": {
            "x86_64": {"baseos": {"url": "https://ext.example.com/x86/baseos/"}},
            "aarch64": {"baseos": {"url": "https://ext.example.com/arm/baseos/"}},
        },
    })
    path = write_status_fixture(tmp_path, data)

    result = validate_repo_contract(data)
    parse = parse_repo_status_external(path)

    if not result["success"] or not parse["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(
            errors=result.get("errors") or parse.get("error"))

    r = parse["result"]
    tl.passed(LOG["contract_validation_ok"], result["details"])
    assert len(r["repo_manager_repos_x86_64"]) == 1
    assert len(r["repo_manager_repos_aarch64"]) == 1


@pytest.mark.sanity
@pytest.mark.order(23)
def test_external_contract_internet_sample():
    """Verify bundled internet sample passes full contract pipeline."""
    tc = TC["external_contract_internet_sample"]
    tl = TestLogger(tc["title"], tc["id"])
    data, path = load_sample_status("repo_status_internet.yml")

    result = validate_repo_contract(data)
    parse = parse_repo_status_external(path)

    if not result["success"] or not parse["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(
            errors=result.get("errors") or parse.get("error"))

    r = parse["result"]
    tl.passed(LOG["contract_sample_ok"].format(sample="internet"), result["details"])
    assert r["cluster_os_versions"] == ["10.0", "10.2"]
    assert r["repo_port"] == 443
    assert len(r["repo_manager_repos_x86_64"]) >= 4


@pytest.mark.sanity
@pytest.mark.order(24)
def test_external_contract_pulp_sample(tmp_path):
    """Verify bundled Pulp sample (Jinja-rendered) passes full pipeline."""
    tc = TC["external_contract_pulp_sample"]
    tl = TestLogger(tc["title"], tc["id"])
    data, path = load_sample_status(
        "repo_status.yml", tmp_path=tmp_path,
        replacements={"{{ admin_nic_ip }}": "192.0.2.10"},
    )

    result = validate_repo_contract(data)
    parse = parse_repo_status_external(path)

    if not result["success"] or not parse["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(
            errors=result.get("errors") or parse.get("error"))

    r = parse["result"]
    tl.passed(LOG["contract_sample_ok"].format(sample="pulp"), result["details"])
    assert r["cluster_os_versions"] == ["10.0", "10.2"]
    assert r["repo_port"] == 2225
    assert r["repo_cert_path"] != ""


@pytest.mark.functional
@pytest.mark.order(25)
def test_external_contract_additional_properties():
    """Verify schema allows additional top-level properties."""
    tc = TC["external_contract_additional_props"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status()
    data["custom_external_metadata"] = {"source": "ci-pipeline", "build_id": 12345}

    result = validate_repo_contract(data)

    if not result["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(errors=result["errors"])

    tl.passed(LOG["contract_producer_ignored_ok"], result["details"])


@pytest.mark.functional
@pytest.mark.order(26)
def test_external_contract_repo_extra_fields(tmp_path):
    """Verify repo entries may carry additional producer metadata."""
    tc = TC["external_contract_repo_extra_fields"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status(repositories={
        "10.0": {"x86_64": {"baseos": {
            "url": "https://ext.example.com/baseos/",
            "priority": 100,
            "gpgcheck": True,
            "sync_timestamp": "2026-11-23T00:00:00Z",
        }}},
    })
    path = write_status_fixture(tmp_path, data)

    result = validate_repo_contract(data)
    parse = parse_repo_status_external(path)

    if not result["success"] or not parse["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(
            errors=result.get("errors") or parse.get("error"))

    tl.passed(LOG["contract_producer_ignored_ok"], result["details"])
    assert parse["result"]["repo_manager_repos_x86_64"][0]["base_url"] == (
        "https://ext.example.com/baseos/"
    )


@pytest.mark.functional
@pytest.mark.live_file
@pytest.mark.order(27)
def test_external_contract_source_is_external():
    """Verify the repo_status.yml under test names repositories on another host.

    **Data source: live file** (requires a completed repo_manager run).
    """
    tc = TC["external_contract_source_is_external"]
    tl = TestLogger(tc["title"], tc["id"])
    config = load_test_config()
    path = live_status_path(config.get("repo_manager_output_path", ""))
    if not os.path.isfile(path):
        msg = (
            f"Live repo_status.yml not found at {path}"
            + (" [REQUIRE_LIVE_REPO_STATUS=1]" if _REQUIRE_LIVE else "")
        )
        if _REQUIRE_LIVE:
            tl.failed(msg, msg)
            pytest.fail(msg)
        tl.skipped(msg)
        pytest.skip(msg)
    with open(path, "r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    result = verify_external_source(data, str(config.get("external_repo_host", "")))
    if not result["success"]:
        tl.failed(LOG["contract_external_source_failed"].format(
            details=result["details"]), result["details"])
    assert result["success"], ASSERT["contract_not_external"].format(
        details=result["details"], hosts=result["hosts"])
    tl.passed(LOG["contract_external_source_ok"].format(details=result["details"]))


@pytest.mark.functional
@pytest.mark.order(28)
def test_external_contract_local_source_rejected():
    """Verify a repo_status.yml whose repositories are on this OIM is rejected."""
    tc = TC["external_contract_local_source_rejected"]
    tl = TestLogger(tc["title"], tc["id"])
    local_ip = next(a for a in sorted(local_addresses())
                    if a.count(".") == 3 and not a.startswith("127."))
    data = minimal_external_status(repositories={
        "10.0": {"x86_64": {"baseos": {"url": f"https://{local_ip}:2225/baseos/"}}},
    })

    result = verify_external_source(data)
    tl.passed(LOG["contract_rejected_ok"], result["details"]) if not result["success"] \
        else tl.failed(LOG["contract_rejection_expected"], result["details"])
    assert not result["success"] and local_ip in result["details"], (
        ASSERT["contract_rejection_expected"])


@pytest.mark.functional
@pytest.mark.order(29)
def test_external_contract_host_pin_mismatch():
    """Verify external_repo_host rejects a repo_status on any other host."""
    tc = TC["external_contract_host_pin_mismatch"]
    tl = TestLogger(tc["title"], tc["id"])
    data = minimal_external_status()

    accepted = verify_external_source(data, "repo.external.example.com")
    rejected = verify_external_source(data, "other.example.com")
    ok = accepted["success"] and not rejected["success"]
    if ok:
        tl.passed(LOG["contract_rejected_ok"], rejected["details"])
    else:
        tl.failed(LOG["contract_rejection_expected"], rejected["details"])
    assert ok, ASSERT["contract_rejection_expected"]
