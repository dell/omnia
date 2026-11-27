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

"""The external-source check of the live repo_status.yml applies only to an external source."""

import pytest

from fvt.validate.contract import test_repo_contract as contract


def _live_file(tmp_path, monkeypatch):
    """Point the check at an existing live file that names a repository on this OIM."""
    path = tmp_path / "repo_status.yml"
    path.write_text("repo_manager: {}\n", encoding="utf-8")
    monkeypatch.setattr(contract, "live_status_path", lambda _output_path: str(path))


def test_external_check_skips_without_an_external_source(monkeypatch, tmp_path):
    """The local repo_manager serves the repositories: skip, do not fail."""
    _live_file(tmp_path, monkeypatch)
    monkeypatch.setattr(contract, "load_test_config", dict)
    monkeypatch.setattr(contract, "_REQUIRE_EXTERNAL", False)
    monkeypatch.setattr(
        contract, "verify_external_source",
        lambda *_args: pytest.fail("the live file must not be judged without an external source"),
    )
    with pytest.raises(pytest.skip.Exception) as skipped:
        contract.test_external_contract_source_is_external()
    reason = str(skipped.value)
    assert "external_repo_host" in reason and "REQUIRE_EXTERNAL_REPO" in reason
    assert "repo_status" not in reason


def test_external_check_fails_when_an_external_host_is_set_and_not_used(monkeypatch, tmp_path):
    """external_repo_host is set and the live file names this OIM: the check fails."""
    _live_file(tmp_path, monkeypatch)
    monkeypatch.setattr(contract, "load_test_config", lambda: {"external_repo_host": "ext.example"})
    seen = []

    def verify(_data, expected_host):
        seen.append(expected_host)
        return {"success": False, "details": "repository host(s) are this OIM", "hosts": []}

    monkeypatch.setattr(contract, "verify_external_source", verify)
    with pytest.raises(AssertionError):
        contract.test_external_contract_source_is_external()
    assert seen == ["ext.example"]


def test_external_check_runs_without_a_host_when_required(monkeypatch, tmp_path):
    """REQUIRE_EXTERNAL_REPO=1 runs the check with no host pin."""
    _live_file(tmp_path, monkeypatch)
    monkeypatch.setattr(contract, "load_test_config", dict)
    monkeypatch.setattr(contract, "_REQUIRE_EXTERNAL", True)
    seen = []

    def verify(_data, expected_host):
        seen.append(expected_host)
        return {"success": True, "details": "external", "hosts": ["ext.example"]}

    monkeypatch.setattr(contract, "verify_external_source", verify)
    contract.test_external_contract_source_is_external()
    assert seen == [""]
