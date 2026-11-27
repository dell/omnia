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

"""The external-source check of the live repo_status.yml is decided by the live file."""

import pytest

from fvt.validate.contract import test_repo_contract as contract


def _setup(monkeypatch, tmp_path, config, hosts, external, required=False):
    """Point the check at a live file with ``hosts``; ``external`` are the hosts not on this OIM."""
    path = tmp_path / "repo_status.yml"
    path.write_text("repo_manager: {}\n", encoding="utf-8")
    monkeypatch.setattr(contract, "live_status_path", lambda _output_path: str(path))
    monkeypatch.setattr(contract, "load_test_config", lambda: config)
    monkeypatch.setattr(contract, "_REQUIRE_EXTERNAL", required)
    monkeypatch.setattr(contract, "status_repo_hosts", lambda _data: set(hosts))
    monkeypatch.setattr(contract, "external_hosts", lambda _hosts: set(external))
    seen = []

    def verify(_data, expected_host):
        seen.append(expected_host)
        return {"success": True, "details": "external", "hosts": sorted(hosts)}

    monkeypatch.setattr(contract, "verify_external_source", verify)
    return seen


def test_external_check_skips_when_every_host_is_this_oim(monkeypatch, tmp_path):
    """The local repo_manager serves the repositories: skip, do not fail."""
    seen = _setup(monkeypatch, tmp_path, {}, {"10.0.0.1"}, set())
    with pytest.raises(pytest.skip.Exception) as skipped:
        contract.test_external_contract_source_is_external()
    reason = str(skipped.value)
    assert "served by this OIM" in reason and "REQUIRE_EXTERNAL_REPO" in reason
    assert "repo_status" not in reason
    assert not seen


def test_external_check_runs_when_a_host_is_another_server(monkeypatch, tmp_path):
    """An external source needs no setting: the file shows it."""
    seen = _setup(monkeypatch, tmp_path, {}, {"repo.other.example"}, {"repo.other.example"})
    contract.test_external_contract_source_is_external()
    assert seen == [""]


def test_external_check_runs_with_a_pinned_host_even_when_local(monkeypatch, tmp_path):
    """external_repo_host is set: the check runs and the pin is passed on."""
    config = {"external_repo_host": " ext.example "}
    seen = _setup(monkeypatch, tmp_path, config, {"10.0.0.1"}, set())
    contract.test_external_contract_source_is_external()
    assert seen == ["ext.example"]


def test_external_check_runs_when_required(monkeypatch, tmp_path):
    """REQUIRE_EXTERNAL_REPO=1 runs the check although every host is this OIM."""
    seen = _setup(monkeypatch, tmp_path, {}, {"10.0.0.1"}, set(), required=True)
    contract.test_external_contract_source_is_external()
    assert seen == [""]


def test_external_check_runs_when_the_file_names_no_host(monkeypatch, tmp_path):
    """A file without repository hosts is not skipped: the contract check reports it."""
    seen = _setup(monkeypatch, tmp_path, {}, set(), set())
    contract.test_external_contract_source_is_external()
    assert seen == [""]
