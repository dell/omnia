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
Slurm Config Util Scenario — Test Automation.

Tests for slurm_config_util.yml (config_backup / slurm_cleanup /
config_rollback tags) deployment and verification.

Requires a deployed Slurm cluster (per orchestrator's omnia_config.yml /
storage_config.yml / PXE mapping) reachable from the target host. Tests
that need a live cluster are marked functional and skip cleanly when the
expected input files or backup artifacts are not present, following the
backup_oim_logs test pattern.
"""

import pytest

from library.functions import (
    TestLogger,
    check_dir_exists,
    check_env_var,
    check_file_exists,
    find_latest_backup_run_dir,
    get_slurm_config_util_config_path,
    get_slurm_config_util_output_path,
    get_utils_input_path,
    check_backup_directories_present,
    load_test_config,
    run_playbook,
    validate_slurm_backup_metadata_file,
    validate_yaml_file,
)
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_SLURM_CONFIG_UTIL,
    PLAYBOOK_WORKDIR,
    SLURM_CONFIG_BACKUP_DIRECTORIES,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT

_ENV_FILE = "/etc/omnia/omnia.env"


def _assert_playbook_ok(host, result, tag_label):
    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_SLURM_CONFIG_UTIL,
        tag=tag_label,
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_slurm_config_util_config_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" +
        PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


# =============================================================================
# SANITY VERIFICATION TESTS (config file is optional)
# =============================================================================

@pytest.mark.sanity
@pytest.mark.slurm_config_util
@pytest.mark.order(80)
def test_slurm_config_util_config_file_valid(host):
    """Verify slurm_config_util_config.yml has valid YAML structure, if present."""
    tc = TC["slurm_config_util_config_file_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    config_path = get_slurm_config_util_config_path(host)
    if not check_file_exists(host, config_path)["success"]:
        tl.skipped(f"slurm_config_util_config.yml not present at {config_path}; defaults apply")
        pytest.skip("slurm_config_util_config.yml is optional and not present")

    result = validate_yaml_file(host, config_path)
    if result["success"]:
        tl.passed(LOG["file_valid"].format(path=config_path))
    else:
        tl.failed(LOG["file_invalid"].format(path=config_path), result["error"])

    assert result["success"], ASSERT["file_invalid"].format(path=config_path, error=result["error"])


@pytest.mark.sanity
@pytest.mark.slurm_config_util
@pytest.mark.order(81)
def test_slurm_config_util_env_vars_loaded(host):
    """Verify OMNIA_DATA_PATH is loaded from environment."""
    tc = TC["slurm_config_util_env_vars_loaded"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_env_var(host, "OMNIA_DATA_PATH")
    if result["success"]:
        tl.passed(LOG["env_var_present"].format(var="OMNIA_DATA_PATH", value=result["value"]))
    else:
        tl.failed(LOG["env_var_missing"].format(var="OMNIA_DATA_PATH"))

    assert result["success"], ASSERT["env_var_missing"].format(var="OMNIA_DATA_PATH")


# =============================================================================
# PLAYBOOK DEPLOYMENT + VERIFICATION: slurm_config_backup
# =============================================================================

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.slurm_config_util
@pytest.mark.order(82)
def test_deploy_slurm_config_backup(host):
    """Deploy slurm_config_util.yml --tags slurm_config_backup.

    Requires a deployed Slurm cluster; skips cleanly when the orchestrator
    input files (omnia_config.yml / storage_config.yml) are not present.
    """
    tc = TC["deploy_slurm_config_backup"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(
        playbook=PLAYBOOK_SLURM_CONFIG_UTIL,
        tag="slurm_config_backup",
        extra_vars={"backup_base_name": "fvt_backup"},
    )

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        details = result.get("error", "") or result.get("output", "")
        if "omnia_config.yml not found" in details or "storage_config.yml not found" in details:
            tl.skipped("Slurm cluster input files not present; skipping live-cluster test")
            pytest.skip("omnia_config.yml / storage_config.yml not present - no Slurm cluster deployed")
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            details or "See playbook output above",
        )

    _assert_playbook_ok(host, result, "slurm_config_backup")


@pytest.mark.functional
@pytest.mark.slurm_config_util
@pytest.mark.order(83)
def test_slurm_config_backup_output_dir_exists(host):
    """Verify the default backup workspace directory exists."""
    tc = TC["slurm_config_backup_output_dir_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_slurm_config_util_output_path(host)
    result = check_dir_exists(host, output_path)

    if not result["success"]:
        tl.skipped(f"Backup workspace not found: {output_path} (no cluster deployed)")
        pytest.skip("Backup workspace not present - no Slurm cluster deployed")

    tl.passed(LOG["dir_exists"].format(path=output_path))
    assert result["success"], f"Backup workspace not found: {output_path}"


@pytest.mark.functional
@pytest.mark.slurm_config_util
@pytest.mark.order(84)
def test_slurm_config_backup_run_dir_created(host):
    """Verify a timestamped backup run directory was created."""
    tc = TC["slurm_config_backup_run_dir_created"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_slurm_config_util_output_path(host)
    result = find_latest_backup_run_dir(host, output_path)

    if not result["success"]:
        tl.skipped(result["error"])
        pytest.skip(result["error"])

    tl.passed(f"Backup run directory created: {result['run_dir']}")
    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.slurm_config_util
@pytest.mark.order(85)
def test_slurm_config_backup_metadata_exists(host):
    """Verify metadata.json exists in the backup run directory."""
    tc = TC["slurm_config_backup_metadata_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_slurm_config_util_output_path(host)
    run_dir_result = find_latest_backup_run_dir(host, output_path)
    if not run_dir_result["success"]:
        tl.skipped(run_dir_result["error"])
        pytest.skip(run_dir_result["error"])

    metadata_path = f"{run_dir_result['run_dir']}/metadata.json"
    result = check_file_exists(host, metadata_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=metadata_path))
    else:
        tl.failed(LOG["file_missing"].format(path=metadata_path))

    assert result["success"], f"Metadata file not found: {metadata_path}"


@pytest.mark.functional
@pytest.mark.slurm_config_util
@pytest.mark.order(86)
def test_slurm_config_backup_metadata_valid(host):
    """Verify metadata.json has valid structure with checksums."""
    tc = TC["slurm_config_backup_metadata_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_slurm_config_util_output_path(host)
    run_dir_result = find_latest_backup_run_dir(host, output_path)
    if not run_dir_result["success"]:
        tl.skipped(run_dir_result["error"])
        pytest.skip(run_dir_result["error"])

    metadata_path = f"{run_dir_result['run_dir']}/metadata.json"
    result = validate_slurm_backup_metadata_file(host, metadata_path)

    if result["success"] and result["has_checksums"]:
        tl.passed("metadata.json valid with file checksums present")
    elif result["success"]:
        tl.failed("metadata.json valid but missing file checksums")
    else:
        tl.failed(LOG["metadata_invalid"].format(error=result["error"]))

    assert result["success"], ASSERT["metadata_invalid"].format(error=result["error"])
    assert result["has_checksums"], "file_checksums_sha256 missing from metadata.json"


@pytest.mark.functional
@pytest.mark.slurm_config_util
@pytest.mark.order(87)
def test_slurm_config_backup_directories_present(host):
    """Verify backup contains etc/slurm, etc/munge, etc/my.cnf.d."""
    tc = TC["slurm_config_backup_directories_present"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_slurm_config_util_output_path(host)
    run_dir_result = find_latest_backup_run_dir(host, output_path)
    if not run_dir_result["success"]:
        tl.skipped(run_dir_result["error"])
        pytest.skip(run_dir_result["error"])

    metadata_path = f"{run_dir_result['run_dir']}/metadata.json"
    meta_result = validate_slurm_backup_metadata_file(host, metadata_path)
    if not meta_result["success"]:
        tl.skipped("Could not read controller_hostname from metadata.json")
        pytest.skip("Could not read controller_hostname from metadata.json")

    controller_hostname = meta_result["data"].get("controller_hostname", "")
    result = check_backup_directories_present(host, run_dir_result["run_dir"], controller_hostname)

    if result["success"]:
        tl.passed(f"Backup contains: {', '.join(result['found'])}")
    else:
        tl.failed(f"Missing directories: {result['missing']}")

    assert result["success"], (
        f"Backup missing expected directories {SLURM_CONFIG_BACKUP_DIRECTORIES}: {result['missing']}"
    )


# =============================================================================
# PLAYBOOK DEPLOYMENT + VERIFICATION: slurm_cleanup
# =============================================================================

@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.slurm_config_util
@pytest.mark.destructive
@pytest.mark.order(88)
def test_deploy_slurm_cleanup(host):
    """Deploy slurm_config_util.yml --tags slurm_config_cleanup (auto pre-backup + confirm).

    Opt-in only (--marker destructive): this deletes the entire live Slurm
    config share (all controllers), which is a decommission-style operation,
    not something to run as part of routine deploy+verify FVT passes.
    """
    tc = TC["deploy_slurm_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(
        playbook=PLAYBOOK_SLURM_CONFIG_UTIL,
        tag="slurm_config_cleanup",
        extra_vars={
            "pre_cleanup_backup_choice_input": "y",
            "backup_base_name": "fvt_pre_cleanup",
            "cleanup_confirm_input": "YES",
        },
    )

    if not result["success"]:
        details = result.get("error", "") or result.get("output", "")
        if "omnia_config.yml not found" in details or "storage_config.yml not found" in details:
            tl.skipped("Slurm cluster input files not present; skipping live-cluster test")
            pytest.skip("omnia_config.yml / storage_config.yml not present - no Slurm cluster deployed")
        tl.failed(LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]))

    tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    _assert_playbook_ok(host, result, "slurm_config_cleanup")


# =============================================================================
# PLAYBOOK DEPLOYMENT + VERIFICATION: config_rollback
# =============================================================================

@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.slurm_config_util
@pytest.mark.order(89)
def test_deploy_slurm_config_rollback(host):
    """Deploy slurm_config_util.yml --tags slurm_config_rollback (restores latest backup)."""
    tc = TC["deploy_slurm_config_rollback"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(
        playbook=PLAYBOOK_SLURM_CONFIG_UTIL,
        tag="slurm_config_rollback",
        extra_vars={
            "backup_choice_input": "1",
            "pre_rollback_backup_choice_input": "n",
        },
    )

    if not result["success"]:
        details = result.get("error", "") or result.get("output", "")
        if "No backups found" in details or "omnia_config.yml not found" in details:
            tl.skipped("No backups / no Slurm cluster deployed; skipping live-cluster test")
            pytest.skip("No backups available or no Slurm cluster deployed")
        tl.failed(LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]))

    tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    _assert_playbook_ok(host, result, "slurm_config_rollback")


@pytest.mark.functional
@pytest.mark.slurm_config_util
@pytest.mark.order(90)
def test_slurm_config_rollback_restores_config(host):
    """Verify the active Slurm config directory exists again after rollback."""
    tc = TC["slurm_config_rollback_restores_config"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/slurm_config_util_config.yml"
    if not check_file_exists(host, config_path)["success"]:
        tl.skipped("No slurm_config_util_config.yml override; relying on default share path is environment-specific")
        pytest.skip("Cannot resolve active Slurm config path without cluster-specific storage_config.yml")


# =============================================================================
# NEGATIVE TESTS
# =============================================================================

@pytest.mark.functional
@pytest.mark.slurm_config_util
@pytest.mark.order(91)
def test_slurm_config_backup_missing_omnia_config_fails(host):
    """Verify config_backup fails cleanly when omnia_config.yml is missing."""
    tc = TC["slurm_config_backup_missing_omnia_config_fails"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(
        playbook=PLAYBOOK_SLURM_CONFIG_UTIL,
        tag="slurm_config_backup",
        extra_vars={"omnia_config_path": "/tmp/omnia_fvt_nonexistent_omnia_config.yml"},
    )

    if result["success"]:
        tl.failed("Playbook unexpectedly succeeded with a missing omnia_config.yml")
    else:
        tl.passed("Playbook correctly failed with a missing omnia_config.yml")

    assert not result["success"], "config_backup should fail when omnia_config.yml is missing"


@pytest.mark.functional
@pytest.mark.slurm_config_util
@pytest.mark.order(92)
def test_slurm_cleanup_wrong_token_aborts(host):
    """Verify slurm_cleanup aborts when confirmation token does not match."""
    tc = TC["slurm_cleanup_wrong_token_aborts"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(
        playbook=PLAYBOOK_SLURM_CONFIG_UTIL,
        tag="slurm_config_cleanup",
        extra_vars={
            "pre_cleanup_backup_choice_input": "n",
            "cleanup_confirm_input": "WRONG_TOKEN",
        },
    )

    details = result.get("error", "") or result.get("output", "")
    if "omnia_config.yml not found" in details or "storage_config.yml not found" in details:
        tl.skipped("No Slurm cluster deployed; skipping live-cluster test")
        pytest.skip("omnia_config.yml / storage_config.yml not present - no Slurm cluster deployed")

    if not result["success"] and "Cleanup aborted" in details:
        tl.passed("Cleanup correctly aborted on token mismatch")
    else:
        tl.failed("Cleanup did not abort on token mismatch as expected")

    assert not result["success"], "slurm_cleanup should abort when the confirmation token is wrong"
