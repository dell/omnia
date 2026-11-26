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

"""Image Build Validate - external repo_manager contract deploy.

Stages an external repo_status.yml (the contract fetched by the contract_remote stage,
else the live repo_manager output) and runs the playbook with ``--tags build``, the real
flow that validates, parses and builds with the contract. All tests need that file: when
it is absent they skip, or fail when REQUIRE_LIVE_REPO_STATUS=1 (set by the SVT).
"""

import copy
import os
import shutil
import tempfile
import uuid

import pytest
import yaml

from library.functions import (
    TestLogger, run_playbook, load_test_config,
)
from library.functions.contract_func import live_status_path, verify_external_source
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    PLAYBOOK_ENTRY_POINT,
    BUILD_LOG_PATH,
    SHARED_PATH,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)

# Staging directory outside OMNIA_DATA_PATH, shared with the contract_remote stage.
_STAGING_DIR = os.path.join(tempfile.gettempdir(), "omnia_contract_test")
_STAGED_FILE = os.path.join(_STAGING_DIR, "repo_status.yml")
_REQUIRE_LIVE = os.environ.get("REQUIRE_LIVE_REPO_STATUS", "") == "1"


def _missing(tl, msg):
    """Fail (REQUIRE_LIVE_REPO_STATUS=1) or skip when the contract file is absent."""
    msg += " [REQUIRE_LIVE_REPO_STATUS=1]" if _REQUIRE_LIVE else ""
    if _REQUIRE_LIVE:
        tl.failed(msg, msg)
        pytest.fail(msg)
    tl.skipped(msg)
    pytest.skip(msg)


def _load_live_status():
    """Return ``(data, path)`` of the staged contract, else of the local repo_manager output."""
    path = _STAGED_FILE
    if not os.path.isfile(path):
        path = live_status_path(load_test_config().get("repo_manager_output_path", ""))
    if not os.path.isfile(path):
        return None, path
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh), path


def _stage_external_status(data):
    """Write ``data`` to the staging directory and return the staged path."""
    os.makedirs(_STAGING_DIR, exist_ok=True)
    with open(_STAGED_FILE, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False)
    return _STAGED_FILE


def _cleanup_staging():
    """Remove the staging directory."""
    shutil.rmtree(_STAGING_DIR, ignore_errors=True)


def _assert_external(tl, data, **kwargs):
    """Fail unless the status names repositories on another host."""
    source = verify_external_source(
        data, str(load_test_config().get("external_repo_host", "")), **kwargs)
    if not source["success"]:
        tl.failed(LOG["contract_external_source_failed"].format(
            details=source["details"]), source["details"])
    assert source["success"], ASSERT["contract_not_external"].format(
        details=source["details"], hosts=source["hosts"])
    tl.info(LOG["contract_external_source_ok"].format(details=source["details"]))


def _build_with_staged(tl, data):
    """Stage ``data``, run ``--tags build`` on it and assert it was consumed and passed."""
    staged_path = _stage_external_status(data)
    tl.info(f"Staged external repo_status at {staged_path}")
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT, tag="build",
        extra_vars={"repo_manager_output_path": staged_path})
    if result["success"]:
        tl.passed(LOG["contract_deploy_ok"].format(
            duration=result["duration"], path=staged_path))
    else:
        tl.failed(LOG["contract_deploy_failed"].format(
            rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"))
    assert f"Repo manager output: {staged_path}" in result.get("output", ""), ASSERT[
        "contract_path_not_consumed"].format(path=staged_path)
    assert result["success"], ASSERT["contract_deploy_failed"].format(
        playbook=PLAYBOOK_ENTRY_POINT, rc=result["rc"], duration=result["duration"],
        path=staged_path,
        log_path=BUILD_LOG_PATH.format(
            shared_path=SHARED_PATH,
            project=load_test_config().get("project_name", "project_default")))


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.live_file
@pytest.mark.phase1
@pytest.mark.order(-1)
def test_deploy_phase1_build(host):
    """Phase 1: build images using the contract fetched by contract_remote."""
    tc = TC["deploy_phase1_build"]
    tl = TestLogger(tc["title"], tc["id"])

    if not os.path.isfile(_STAGED_FILE):
        _missing(tl, f"Staged repo_status.yml not found at {_STAGED_FILE}. The "
                     "contract_remote stage must fetch it from the external OIM first.")
    with open(_STAGED_FILE, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    _assert_external(tl, data, skip_cert=True)

    data["custom_external_metadata"] = {
        "source": "contract-fvt-phase1",
        "producer_oim": load_test_config().get("external_oim", {}).get("ip", "unknown"),
        "run_nonce": uuid.uuid4().hex,
    }
    _build_with_staged(tl, data)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.live_file
@pytest.mark.order(0)
def test_deploy_external_contract(host):
    """Deploy --tags build with external repo_status (live or staged)."""
    tc = TC["deploy_external_contract"]
    tl = TestLogger(tc["title"], tc["id"])

    data, source_path = _load_live_status()
    if data is None:
        _missing(tl, f"Live repo_status.yml not found at {source_path}")
    # A staged contract was already verified by the contract_remote stage.
    if not source_path.startswith(_STAGING_DIR):
        _assert_external(tl, data)

    data["custom_external_metadata"] = {
        "source": "contract-fvt",
        "producer_version": "external-1.0",
        "build_id": 99999,
        "run_nonce": uuid.uuid4().hex,
    }
    if not data.get("execution_contexts"):
        data["execution_contexts"] = [
            {"context_id": "external", "os_type": data.get("cluster_os_type", "rhel"),
             "os_version": "10.0", "architectures": ["x86_64"]},
        ]
    _build_with_staged(tl, data)


def _first_repo_entry(data):
    """Return the first repository entry (dict with ``url``) of a status dict."""
    for versions in data["repositories"].values():
        for arches in versions.values():
            for entry in arches.values():
                if isinstance(entry, dict) and "url" in entry:
                    return entry
    raise AssertionError("no repository entry with a url in repo_status.yml")


def _run_negative_control(tc_key, mutate, expected_task, expected_text):
    """Stage a mutated repo_status.yml and expect --tags build to fail."""
    tc = TC[tc_key]
    tl = TestLogger(tc["title"], tc["id"])

    data, source_path = _load_live_status()
    if data is None:
        _missing(tl, f"Live repo_status.yml not found at {source_path}")
    # A staged contract already proves the playbook reads the staged file.
    if source_path.startswith(_STAGING_DIR):
        msg = "Negative controls skipped for staged contract (Phase 1 flow)"
        tl.skipped(msg)
        pytest.skip(msg)

    data = copy.deepcopy(data)
    mutate(data)
    staged_path = _stage_external_status(data)
    tl.info(f"Staged tampered repo_status at {staged_path}")

    try:
        result = run_playbook(
            playbook=PLAYBOOK_ENTRY_POINT, tag="build",
            extra_vars={"repo_manager_output_path": staged_path})
        output = result.get("output", "")
        failed_here = (not result["success"] and expected_task in output
                       and expected_text in output)
        if failed_here:
            tl.passed(LOG["contract_negative_ok"].format(
                task=expected_task, text=expected_text))
        else:
            tl.failed(LOG["contract_negative_failed"].format(rc=result["rc"]),
                      "Playbook did not fail on the staged file as expected")
        assert failed_here, ASSERT["contract_negative_failed"].format(
            task=expected_task, text=expected_text, rc=result["rc"], path=staged_path)
    finally:
        _cleanup_staging()


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.live_file
@pytest.mark.order(1)
def test_deploy_external_contract_sentinel_url(host):
    """A sentinel repo URL only present in the staged file must be reported.

    **Data source: live file** (requires a completed repo_manager run).
    """
    sentinel = f"https://127.0.0.1:1/contract-sentinel-{uuid.uuid4().hex[:12]}/"

    def mutate(data):
        _first_repo_entry(data)["url"] = sentinel

    _run_negative_control(
        "deploy_external_contract_sentinel_url", mutate,
        expected_task="Fail if any repo URLs are unreachable",
        expected_text=sentinel,
    )


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.live_file
@pytest.mark.order(2)
def test_deploy_external_contract_invalid_status(host):
    """A staged status with overall_status failed must stop at the contract gate.

    **Data source: live file** (requires a completed repo_manager run).
    """
    def mutate(data):
        data["overall_status"] = "failed"

    _run_negative_control(
        "deploy_external_contract_invalid_status", mutate,
        expected_task="Validate repo_status.yml contract",
        expected_text="overall_status",
    )
    _cleanup_staging()
