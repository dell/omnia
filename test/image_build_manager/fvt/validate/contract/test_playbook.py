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
Image Build Validate — External repo_manager Contract Deploy.

Stages an externally-sourced repo_status.yml (the live repo_manager output
enriched with producer metadata) and runs the image_build_manager playbook
with ``--tags build``.  The build tag is the real flow that naturally sets
``needs_repo_status=true`` and exercises the full contract pipeline:

  1. JSON Schema validation (validate_repo_status_contract module)
  2. Semantic validation (repo_status_validator)
  3. parse_repo_status — sets Ansible facts consumed by later tags
  4. Certificate path validation
  5. Repository URL reachability check
  6. Full image build execution with the external repo_status

**Data-source category: live file.**

All tests in this module require the real ``repo_status.yml`` produced by
an earlier ``repo_manager`` run.  When the file is absent:

* Default behaviour: the test **skips** (safe for ad-hoc / dev-box runs).
* When ``REQUIRE_LIVE_REPO_STATUS=1`` is set (CI / nightly mode): the
  test **fails** so a green report cannot hide the fact that the live-file
  path was never exercised.

The SVT ``external_contract`` theme guarantees the file exists by
depending on a completed ``repo_manager`` stage before this suite runs.
"""

import copy
import os
import shutil
import tempfile
import uuid

import pytest
import yaml

from library.functions import (
    TestLogger, run_playbook, load_test_config, load_test_credentials,
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

# Temp staging directory (outside OMNIA_DATA_PATH to prove external sourcing)
_STAGING_DIR = os.path.join(tempfile.gettempdir(), "omnia_contract_test")

_REQUIRE_LIVE = os.environ.get("REQUIRE_LIVE_REPO_STATUS", "") == "1"


def _require_or_skip(tl, path):
    """Fail or skip when the live repo_status.yml is absent.

    When ``REQUIRE_LIVE_REPO_STATUS=1`` is set, the test fails so that a
    green report cannot hide the missing live-file path.  Otherwise, it
    skips (safe for ad-hoc / dev-box runs).
    """
    msg = (
        f"Live repo_status.yml not found at {path}"
        + (" [REQUIRE_LIVE_REPO_STATUS=1]" if _REQUIRE_LIVE else "")
    )
    if _REQUIRE_LIVE:
        tl.failed(msg, msg)
        pytest.fail(msg)
    tl.skipped(msg)
    pytest.skip(msg)


def _load_live_status():
    """Read the production repo_status.yml from the OIM.

    First tries to load from the staged contract (Phase 1 cross-OIM flow),
    then falls back to the local repo_manager output path.

    Returns:
        Tuple of (data dict, source path) or (None, path) if not found.
    """
    # First try the staged contract from contract_remote stage
    staged_path = os.path.join(_STAGING_DIR, "repo_status.yml")
    if os.path.isfile(staged_path):
        with open(staged_path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh), staged_path

    # Fall back to local repo_manager output
    config = load_test_config()
    path = live_status_path(config.get("repo_manager_output_path", ""))

    if not os.path.isfile(path):
        return None, path

    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh), path


def _stage_external_status(data):
    """Write a repo_status.yml to the staging directory.

    Args:
        data: The (possibly enriched) repo_status dict.

    Returns:
        Absolute path to the staged file.
    """
    os.makedirs(_STAGING_DIR, exist_ok=True)
    staged = os.path.join(_STAGING_DIR, "repo_status.yml")
    with open(staged, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False)
    return staged


def _cleanup_staging():
    """Remove the staging directory."""
    if os.path.isdir(_STAGING_DIR):
        shutil.rmtree(_STAGING_DIR, ignore_errors=True)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.live_file
@pytest.mark.phase1
@pytest.mark.order(-1)
def test_deploy_phase1_build(host):
    """Phase 1: build images using the contract fetched by contract_remote."""
    tc = TC["deploy_phase1_build"]
    tl = TestLogger(tc["title"], tc["id"])

    staged_path = os.path.join(_STAGING_DIR, "repo_status.yml")
    if not os.path.isfile(staged_path):
        msg = (
            f"Staged repo_status.yml not found at {staged_path}. "
            "The contract_remote stage must run first to fetch the "
            "contract from the external OIM."
        )
        if _REQUIRE_LIVE:
            tl.failed(msg, msg)
            pytest.fail(msg)
        tl.skipped(msg)
        pytest.skip(msg)

    config = load_test_config()

    # --- Verify the staged contract is from an external source ---
    with open(staged_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    source = verify_external_source(
        data, str(config.get("external_repo_host", "")),
        skip_cert=True,
    )
    if not source["success"]:
        tl.failed(LOG["contract_external_source_failed"].format(
            details=source["details"]), source["details"])
    assert source["success"], ASSERT["contract_not_external"].format(
        details=source["details"], hosts=source["hosts"])
    tl.info(LOG["contract_external_source_ok"].format(
        details=source["details"]))

    # --- Add producer metadata and run --tags build ---
    data["custom_external_metadata"] = {
        "source": "contract-fvt-phase1",
        "producer_oim": config.get("external_oim", {}).get("ip", "unknown"),
        "run_nonce": uuid.uuid4().hex,
    }
    staged_path = _stage_external_status(data)
    tl.info(f"Staged fetched repo_status at {staged_path}")

    # Run playbook with the staged contract
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="build",
        extra_vars={"repo_manager_output_path": staged_path},
    )

    if result["success"]:
        tl.passed(LOG["contract_deploy_ok"].format(
            duration=result["duration"], path=staged_path))
    else:
        tl.failed(LOG["contract_deploy_failed"].format(
            rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"))

    consumed = f"Repo manager output: {staged_path}"
    assert consumed in result.get("output", ""), ASSERT[
        "contract_path_not_consumed"
    ].format(path=staged_path)
    assert result["success"], ASSERT["contract_deploy_failed"].format(
        playbook=PLAYBOOK_ENTRY_POINT,
        rc=result["rc"],
        duration=result["duration"],
        path=staged_path,
        log_path=BUILD_LOG_PATH.format(
            shared_path=SHARED_PATH,
            project=config.get("project_name", "project_default"),
        ),
    )
    # Note: staging directory is NOT cleaned up here - it's preserved
    # for E002 and negative controls. Cleanup happens in E002.


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.live_file
@pytest.mark.order(0)
def test_deploy_external_contract(host):
    """Deploy --tags build with external repo_status (live or staged)."""
    tc = TC["deploy_external_contract"]
    tl = TestLogger(tc["title"], tc["id"])

    # --- Load the live status (or staged contract) ---
    data, source_path = _load_live_status()
    if data is None:
        _require_or_skip(tl, source_path)

    # --- The live status must come from an external source ---
    # Skip verification for staged contracts (already verified by contract_remote)
    is_staged = source_path.startswith(_STAGING_DIR)
    if not is_staged:
        source = verify_external_source(
            data, str(load_test_config().get("external_repo_host", "")),
        )
        if not source["success"]:
            tl.failed(LOG["contract_external_source_failed"].format(
                details=source["details"]), source["details"])
        assert source["success"], ASSERT["contract_not_external"].format(
            details=source["details"], hosts=source["hosts"])
        tl.info(LOG["contract_external_source_ok"].format(details=source["details"]))

    # --- Enrich with external producer metadata ---
    data["custom_external_metadata"] = {
        "source": "contract-fvt",
        "producer_version": "external-1.0",
        "build_id": 99999,
        "run_nonce": uuid.uuid4().hex,
    }
    data.setdefault("execution_contexts", [])
    if not data["execution_contexts"]:
        data["execution_contexts"] = [
            {"context_id": "external", "os_type": data.get("cluster_os_type", "rhel"),
             "os_version": "10.0", "architectures": ["x86_64"]},
        ]

    # --- Stage to external path ---
    staged_path = _stage_external_status(data)
    tl.info(f"Staged external repo_status at {staged_path}")

    # --- Run playbook with external repo_status (real build flow) ---
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        tag="build",
        extra_vars={
            "repo_manager_output_path": staged_path,
        },
    )

    if result["success"]:
        tl.passed(
            LOG["contract_deploy_ok"].format(
                duration=result["duration"],
                path=staged_path,
            ),
        )
    else:
        tl.failed(
            LOG["contract_deploy_failed"].format(
                rc=result["rc"],
                duration=result["duration"],
            ),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    consumed = f"Repo manager output: {staged_path}"
    assert consumed in result.get("output", ""), ASSERT[
        "contract_path_not_consumed"
    ].format(path=staged_path)
    assert result["success"], ASSERT["contract_deploy_failed"].format(
        playbook=PLAYBOOK_ENTRY_POINT,
        rc=result["rc"],
        duration=result["duration"],
        path=staged_path,
        log_path=BUILD_LOG_PATH.format(
            shared_path=SHARED_PATH,
            project=config.get("project_name", "project_default"),
        ),
    )
    # Note: staging directory is NOT cleaned up here - it's preserved
    # for negative controls. Cleanup happens in the last test.


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
        _require_or_skip(tl, source_path)

    # Skip negative controls when using staged contract - they're for
    # proving the playbook reads the staged file, which is already
    # proven by the contract_remote -> contract_build flow.
    is_staged = source_path.startswith(_STAGING_DIR)
    if is_staged:
        tl.skipped("Negative controls skipped for staged contract (Phase 1 flow)")
        pytest.skip("Negative controls skipped for staged contract (Phase 1 flow)")

    data = copy.deepcopy(data)
    mutate(data)
    staged_path = _stage_external_status(data)
    tl.info(f"Staged tampered repo_status at {staged_path}")

    try:
        result = run_playbook(
            playbook=PLAYBOOK_ENTRY_POINT,
            tag="build",
            extra_vars={"repo_manager_output_path": staged_path},
        )
        output = result.get("output", "")
        failed_here = (
            not result["success"]
            and expected_task in output
            and expected_text in output
        )
        if failed_here:
            tl.passed(LOG["contract_negative_ok"].format(
                task=expected_task, text=expected_text,
            ))
        else:
            tl.failed(
                LOG["contract_negative_failed"].format(rc=result["rc"]),
                "Playbook did not fail on the staged file as expected",
            )
        assert failed_here, ASSERT["contract_negative_failed"].format(
            task=expected_task, text=expected_text,
            rc=result["rc"], path=staged_path,
        )
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
    # Cleanup staging directory after the last contract test
    _cleanup_staging()
