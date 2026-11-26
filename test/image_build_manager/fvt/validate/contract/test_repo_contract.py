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

"""Image Build Validate - external repo_manager contract verification.

image_build_manager must consume a repo_status.yml produced elsewhere (another
OIM, a CI artifact, an operator file), whatever optional sections or extra
producer fields it carries. Pipeline under test: JSON Schema, semantic
validation, then parse_repo_status.

Data sources (20 tests): synthetic dicts (V005-V017, V020, V021, V023, V024),
bundled samples (V018, V019) and the live file (V022, the only test that needs
a completed repo_manager run). V022 skips when the file is absent, or fails when
REQUIRE_LIVE_REPO_STATUS=1 is set.
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
_EXT = "https://ext.example.com"


def _logger(key):
    """Return the TestLogger of the test case ``key``."""
    return TestLogger(TC[key]["title"], TC[key]["id"])


def _accept(tl, data, tmp_path=None, path=None, ok="contract_validation_ok", **fmt):
    """Validate (and parse) a status dict, fail with the shared messages, return the parse."""
    result = validate_repo_contract(data)
    if result["success"] and tmp_path is not None:
        path = write_status_fixture(tmp_path, data)
    parse = parse_repo_status_external(path) if path else {"success": True, "result": {}}
    if not result["success"]:
        tl.failed(LOG["contract_validation_failed"], result["details"])
        assert False, ASSERT["contract_failed"].format(errors=result["errors"])
    if not parse["success"]:
        tl.failed(LOG["contract_parse_failed"], parse["details"])
        assert False, ASSERT["contract_parse_failed"].format(error=parse["error"])
    tl.passed(LOG[ok].format(**fmt), result["details"])
    return parse["result"]


def _reject(tl, data, expect=None):
    """Assert that the contract rejects ``data`` (optionally naming ``expect``)."""
    result = validate_repo_contract(data)
    if result["success"]:
        tl.failed(LOG["contract_rejection_expected"])
        assert False, ASSERT["contract_rejection_expected"]
    tl.passed(LOG["contract_rejected_ok"], result["details"])
    assert expect is None or any(expect in e for e in result["errors"])


def _repos(**versions):
    """Return a ``repositories`` mapping of ``{version: {arch: {name: url}}}``."""
    return {ver: {arch: {name: {"url": url} for name, url in repos.items()}
                  for arch, repos in arches.items()} for ver, arches in versions.items()}


@pytest.mark.sanity
@pytest.mark.order(10)
def test_external_contract_minimal(tmp_path):
    """Verify minimal external repo_status.yml passes full contract."""
    r = _accept(_logger("external_contract_minimal"), minimal_external_status(), tmp_path)
    assert r["cluster_os_type"] == "rhel"
    assert r["cluster_os_versions"] == ["10.0"]
    assert r["repo_port"] == 443
    assert len(r["repo_manager_repos_x86_64"]) == 1


@pytest.mark.sanity
@pytest.mark.order(11)
def test_external_contract_multi_version(tmp_path):
    """Verify external status with two OS versions parses correctly."""
    data = minimal_external_status(repositories=_repos(**{
        "10.0": {"x86_64": {"baseos": f"{_EXT}/10.0/baseos/",
                            "appstream": f"{_EXT}/10.0/appstream/"}},
        "10.2": {"x86_64": {"baseos": f"{_EXT}/10.2/baseos/"}},
    }))
    r = _accept(_logger("external_contract_multi_version"), data, tmp_path)
    assert r["cluster_os_versions"] == ["10.0", "10.2"]
    names = {repo["name"] for repo in r["repo_manager_repos_x86_64"]}
    assert {"10_0_baseos", "10_2_baseos"} <= names


@pytest.mark.functional
@pytest.mark.order(12)
def test_external_contract_aarch64_only(tmp_path):
    """Verify external status with aarch64-only repos is valid."""
    data = minimal_external_status(repositories=_repos(
        **{"10.0": {"aarch64": {"baseos": f"{_EXT}/aarch64/baseos/"}}}))
    r = _accept(_logger("external_contract_aarch64_only"), data, tmp_path)
    assert len(r["repo_manager_repos_x86_64"]) == 0
    assert len(r["repo_manager_repos_aarch64"]) == 1


@pytest.mark.sanity
@pytest.mark.order(13)
def test_external_contract_custom_port(tmp_path):
    """Verify explicit repo_manager.port propagates to consumer."""
    data = minimal_external_status(repo_manager={"port": 8443})
    r = _accept(_logger("external_contract_custom_port"), data, tmp_path,
                ok="contract_port_ok", port=8443)
    assert r["repo_port"] == 8443


@pytest.mark.functional
@pytest.mark.order(14)
def test_external_contract_url_port(tmp_path):
    """Verify port derived from URL when repo_manager section absent."""
    data = minimal_external_status(repositories=_repos(
        **{"10.0": {"x86_64": {"baseos": "https://repo.example.com:9443/baseos/"}}}))
    r = _accept(_logger("external_contract_url_port"), data, tmp_path,
                ok="contract_port_ok", port=9443)
    assert r["repo_port"] == 9443


@pytest.mark.sanity
@pytest.mark.order(15)
def test_external_contract_cert_path(tmp_path):
    """Verify certificate metadata propagates to consumer."""
    data = minimal_external_status(repo_manager={"port": 2225, "certificates": {
        "server_crt": "/external/certs/ca-bundle.crt", "certs_dir": "/external/certs"}})
    r = _accept(_logger("external_contract_cert_path"), data, tmp_path, ok="contract_cert_ok")
    assert r["repo_cert_path"] == "/external/certs/ca-bundle.crt"
    assert r["repo_port"] == 2225


@pytest.mark.functional
@pytest.mark.order(16)
def test_external_contract_empty_cert(tmp_path):
    """Verify internet source with empty cert returns empty string."""
    data = minimal_external_status(repo_manager={
        "port": "", "certificates": {"server_crt": "", "certs_dir": ""}})
    r = _accept(_logger("external_contract_empty_cert"), data, tmp_path)
    assert r["repo_cert_path"] == ""


@pytest.mark.functional
@pytest.mark.order(17)
def test_external_contract_producer_metadata_ignored(tmp_path):
    """Verify producer-owned fields are ignored by consumer."""
    data = minimal_external_status(
        execution_contexts=[{"context_id": "ext", "os_type": "rhel", "os_version": "10.0",
                             "architectures": ["x86_64"]}],
        overall_status_by_version={"10.0": "success"}, repo_config="full",
        file_repos={"x86_64": {}}, registries={}, future_producer_field={"layout": "v3"})
    r = _accept(_logger("external_contract_producer_ignored"), data, tmp_path,
                ok="contract_producer_ignored_ok")
    assert r["cluster_os_type"] == "rhel"
    assert r["cluster_os_versions"] == ["10.0"]


@pytest.mark.functional
@pytest.mark.order(18)
def test_external_contract_priority(tmp_path):
    """Verify priority values propagate from external source."""
    data = minimal_external_status(repositories=_repos(**{"10.0": {"x86_64": {
        "baseos": f"{_EXT}/baseos/", "custom": f"{_EXT}/custom/"}}}))
    entries = data["repositories"]["10.0"]["x86_64"]
    entries["baseos"]["priority"], entries["custom"]["priority"] = 50, 100
    r = _accept(_logger("external_contract_priority"), data, tmp_path)
    repos = {repo["name"]: repo for repo in r["repo_manager_repos_x86_64"]}
    assert repos["10_0_baseos"].get("priority") == "50"
    assert repos["10_0_custom"].get("priority") == "100"


@pytest.mark.sanity
@pytest.mark.order(19)
def test_external_contract_failed_status_rejected():
    """Verify external status with overall_status != success is rejected."""
    _reject(_logger("external_contract_failed_rejected"),
            minimal_external_status(overall_status="failed"), "success")


@pytest.mark.sanity
@pytest.mark.order(20)
def test_external_contract_missing_repos_rejected():
    """Verify external status without repositories is rejected."""
    _reject(_logger("external_contract_missing_repos"),
            {"overall_status": "success", "cluster_os_type": "rhel"}, "repositories")


@pytest.mark.functional
@pytest.mark.order(21)
def test_external_contract_empty_repos_rejected():
    """Verify external status with empty repositories is rejected."""
    _reject(_logger("external_contract_empty_repos"), minimal_external_status(repositories={}))


@pytest.mark.functional
@pytest.mark.order(22)
def test_external_contract_mixed_arch(tmp_path):
    """Verify mixed x86_64 + aarch64 builds separate repo lists."""
    data = minimal_external_status(repositories=_repos(**{"10.0": {
        "x86_64": {"baseos": f"{_EXT}/x86/baseos/"},
        "aarch64": {"baseos": f"{_EXT}/arm/baseos/"}}}))
    r = _accept(_logger("external_contract_mixed_arch"), data, tmp_path)
    assert len(r["repo_manager_repos_x86_64"]) == 1
    assert len(r["repo_manager_repos_aarch64"]) == 1


@pytest.mark.sanity
@pytest.mark.order(23)
def test_external_contract_internet_sample():
    """Verify bundled internet sample passes full contract pipeline."""
    data, path = load_sample_status("repo_status_internet.yml")
    r = _accept(_logger("external_contract_internet_sample"), data, path=path,
                ok="contract_sample_ok", sample="internet")
    assert r["cluster_os_versions"] == ["10.0", "10.2"]
    assert r["repo_port"] == 443
    assert len(r["repo_manager_repos_x86_64"]) >= 4


@pytest.mark.sanity
@pytest.mark.order(24)
def test_external_contract_pulp_sample(tmp_path):
    """Verify bundled Pulp sample (Jinja-rendered) passes full pipeline."""
    data, path = load_sample_status(
        "repo_status.yml", tmp_path=tmp_path,
        replacements={"{{ admin_nic_ip }}": "192.0.2.10"})
    r = _accept(_logger("external_contract_pulp_sample"), data, path=path,
                ok="contract_sample_ok", sample="pulp")
    assert r["cluster_os_versions"] == ["10.0", "10.2"]
    assert r["repo_port"] == 2225
    assert r["repo_cert_path"] != ""


@pytest.mark.functional
@pytest.mark.order(25)
def test_external_contract_additional_properties():
    """Verify schema allows additional top-level properties."""
    data = minimal_external_status(
        custom_external_metadata={"source": "ci-pipeline", "build_id": 12345})
    _accept(_logger("external_contract_additional_props"), data, ok="contract_producer_ignored_ok")


@pytest.mark.functional
@pytest.mark.order(26)
def test_external_contract_repo_extra_fields(tmp_path):
    """Verify repo entries may carry additional producer metadata."""
    data = minimal_external_status(repositories=_repos(
        **{"10.0": {"x86_64": {"baseos": f"{_EXT}/baseos/"}}}))
    data["repositories"]["10.0"]["x86_64"]["baseos"].update(
        priority=100, gpgcheck=True)
    r = _accept(_logger("external_contract_repo_extra_fields"), data, tmp_path,
                ok="contract_producer_ignored_ok")
    assert r["repo_manager_repos_x86_64"][0]["base_url"] == f"{_EXT}/baseos/"


@pytest.mark.functional
@pytest.mark.live_file
@pytest.mark.order(27)
def test_external_contract_source_is_external():
    """Verify the repo_status.yml under test names repositories on another host.

    **Data source: live file** (requires a completed repo_manager run).

    The success path needs a repo_status.yml produced by a separate Repo Manager
    host. On a single-OIM box the repositories resolve to this OIM, so the check
    correctly fails; a skip means no live file exists, not that nothing was checked.
    """
    tl = _logger("external_contract_source_is_external")
    config = load_test_config()
    path = live_status_path(config.get("repo_manager_output_path", ""))
    if not os.path.isfile(path):
        msg = f"Live repo_status.yml not found at {path}" + (
            " [REQUIRE_LIVE_REPO_STATUS=1]" if _REQUIRE_LIVE else "")
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
    tl = _logger("external_contract_local_source_rejected")
    local_ip = next(a for a in sorted(local_addresses())
                    if a.count(".") == 3 and not a.startswith("127."))
    data = minimal_external_status(repositories=_repos(
        **{"10.0": {"x86_64": {"baseos": f"https://{local_ip}:2225/baseos/"}}}))

    result = verify_external_source(data)
    (tl.failed if result["success"] else tl.passed)(
        LOG["contract_rejection_expected" if result["success"] else "contract_rejected_ok"],
        result["details"])
    assert not result["success"] and local_ip in result["details"], (
        ASSERT["contract_rejection_expected"])


@pytest.mark.functional
@pytest.mark.order(29)
def test_external_contract_host_pin_mismatch():
    """Verify external_repo_host rejects a repo_status on any other host."""
    tl = _logger("external_contract_host_pin_mismatch")
    data = minimal_external_status()

    accepted = verify_external_source(data, "repo.external.example.com")
    rejected = verify_external_source(data, "other.example.com")
    ok = accepted["success"] and not rejected["success"]
    (tl.passed if ok else tl.failed)(
        LOG["contract_rejected_ok" if ok else "contract_rejection_expected"],
        rejected["details"])
    assert ok, ASSERT["contract_rejection_expected"]
