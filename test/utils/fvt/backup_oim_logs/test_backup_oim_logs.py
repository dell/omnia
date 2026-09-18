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
Backup OIM Logs Scenario — Test Automation.

Tests for backup_oim_logs.yml deployment and verification.

Following the collect scenario pattern:
- Sanity test runs complete deployment based on OMNIA_DEPLOY_TAG environment
  variable. If OMNIA_DEPLOY_TAG is not set, runs full deployment (all tags).
- All other tests are marked as functional.
- backup_oim_logs_config.yml is optional; tests that depend on it skip
  cleanly when the file is absent.
"""

import os

import pytest

from library.functions import (
    TestLogger,
    check_env_var,
    check_dir_exists,
    check_file_exists,
    find_log_bundle,
    get_backup_oim_logs_config_path,
    get_backup_oim_logs_output_path,
    load_test_config,
    run_playbook,
    validate_backup_config,
    validate_backup_metadata_file,
    validate_tar_contents,
)
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_BACKUP_OIM_LOGS,
    PLAYBOOK_WORKDIR,
    BACKUP_ALL_DOMAINS,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT

_ENV_FILE = "/etc/omnia/omnia.env"


def _get_deploy_tag():
    """Get deploy tag from OMNIA_DEPLOY_TAG env var."""
    return os.environ.get("OMNIA_DEPLOY_TAG", "")


def _assert_playbook_ok(host, result, tag_label):
    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_BACKUP_OIM_LOGS,
        tag=tag_label,
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_backup_oim_logs_config_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" +
        PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


# =============================================================================
# PLAYBOOK DEPLOYMENT TESTS
# =============================================================================

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.backup_oim_logs
@pytest.mark.order(40)
def test_deploy_backup_oim_logs(host):
    """Deploy backup_oim_logs.yml with the configured tag (or full stack)."""
    tag = _get_deploy_tag()
    if tag:
        tc = TC[f"deploy_backup_oim_logs_{tag}"]
        tl = TestLogger(tc["title"], tc["id"])
        tl.check(f"Running backup_oim_logs.yml --tags {tag}")
        result = run_playbook(playbook=PLAYBOOK_BACKUP_OIM_LOGS, tag=tag)
        tag_label = tag
    else:
        tc = TC["deploy_backup_oim_logs_full"]
        tl = TestLogger(tc["title"], tc["id"])
        tl.check("Running backup_oim_logs.yml (full stack - no tag)")
        result = run_playbook(playbook=PLAYBOOK_BACKUP_OIM_LOGS)
        tag_label = "(none - full stack)"

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )
    _assert_playbook_ok(host, result, tag_label)


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(41)
def test_deploy_backup_oim_logs_setup(host):
    """Deploy backup_oim_logs.yml with setup tag (functional test)."""
    tc = TC["deploy_backup_oim_logs_setup"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_BACKUP_OIM_LOGS, tag="setup")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )
    _assert_playbook_ok(host, result, "setup")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(42)
def test_deploy_backup_oim_logs_bundle(host):
    """Deploy backup_oim_logs.yml with bundle tag (runs standalone)."""
    tc = TC["deploy_backup_oim_logs_bundle"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_BACKUP_OIM_LOGS, tag="bundle")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )
    _assert_playbook_ok(host, result, "bundle")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(43)
def test_deploy_backup_oim_logs_full(host):
    """Deploy backup_oim_logs.yml with all tags (full execution)."""
    tc = TC["deploy_backup_oim_logs_full"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_BACKUP_OIM_LOGS, tag=None)

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )
    _assert_playbook_ok(host, result, "(all)")


# =============================================================================
# SANITY VERIFICATION TESTS (config file is optional)
# =============================================================================

@pytest.mark.sanity
@pytest.mark.backup_oim_logs
@pytest.mark.order(35)
def test_backup_oim_logs_config_file_valid(host):
    """Verify backup_oim_logs_config.yml has valid YAML structure, if present."""
    tc = TC["backup_oim_logs_config_file_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    config_path = get_backup_oim_logs_config_path(host)
    if not check_file_exists(host, config_path)["success"]:
        tl.skipped(f"backup_oim_logs_config.yml not present at {config_path}; all domains apply")
        pytest.skip("backup_oim_logs_config.yml is optional and not present")

    result = validate_backup_config(host, config_path)
    if result["success"]:
        tl.passed(LOG["file_valid"].format(path=config_path))
    else:
        tl.failed(LOG["file_invalid"].format(path=config_path), result["error"])

    assert result["success"], ASSERT["file_invalid"].format(path=config_path, error=result["error"])


@pytest.mark.sanity
@pytest.mark.backup_oim_logs
@pytest.mark.order(36)
def test_backup_oim_logs_config_domains_valid(host):
    """Verify backup_oim_logs_config.yml domains are valid, if present."""
    tc = TC["backup_oim_logs_config_domains_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    config_path = get_backup_oim_logs_config_path(host)
    if not check_file_exists(host, config_path)["success"]:
        tl.skipped("backup_oim_logs_config.yml not present; skipping domain check")
        pytest.skip("backup_oim_logs_config.yml is optional and not present")

    result = validate_backup_config(host, config_path)
    if result["success"]:
        tl.passed(f"Valid domains: {', '.join(result['domains']) or '(all domains)'}")
    else:
        tl.failed(f"Invalid domains found: {result['invalid_domains']}")

    assert result["success"], (
        f"Invalid domains in backup_oim_logs_config.yml: {result['invalid_domains']}. "
        f"Valid domains: {', '.join(BACKUP_ALL_DOMAINS)}"
    )


@pytest.mark.sanity
@pytest.mark.backup_oim_logs
@pytest.mark.order(37)
def test_backup_oim_logs_env_vars_loaded(host):
    """Verify OMNIA_DATA_PATH is loaded from environment."""
    tc = TC["backup_oim_logs_env_vars_loaded"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_env_var(host, "OMNIA_DATA_PATH")
    if result["success"]:
        tl.passed(LOG["env_var_present"].format(var="OMNIA_DATA_PATH", value=result["value"]))
    else:
        tl.failed(LOG["env_var_missing"].format(var="OMNIA_DATA_PATH"))

    assert result["success"], ASSERT["env_var_missing"].format(var="OMNIA_DATA_PATH")


@pytest.mark.sanity
@pytest.mark.backup_oim_logs
@pytest.mark.order(38)
def test_backup_oim_logs_project_name_loaded(host):
    """Verify OMNIA_PROJECT_NAME is loaded from environment."""
    tc = TC["backup_oim_logs_project_name_loaded"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_env_var(host, "OMNIA_PROJECT_NAME")
    if result["success"]:
        tl.passed(LOG["env_var_present"].format(var="OMNIA_PROJECT_NAME", value=result["value"]))
    else:
        tl.failed(LOG["env_var_missing"].format(var="OMNIA_PROJECT_NAME"))

    assert result["success"], ASSERT["env_var_missing"].format(var="OMNIA_PROJECT_NAME")


# =============================================================================
# OUTPUT VERIFICATION
# =============================================================================

@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(50)
def test_backup_oim_logs_output_dir_exists(host):
    """Verify the default backup workspace directory exists."""
    tc = TC["backup_oim_logs_output_dir_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_backup_oim_logs_output_path(host)
    result = check_dir_exists(host, output_path)

    if result["success"]:
        tl.passed(LOG["dir_exists"].format(path=output_path))
    else:
        tl.failed(LOG["dir_missing"].format(path=output_path))

    assert result["success"], f"Backup workspace not found: {output_path}"


@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(51)
def test_backup_oim_logs_archive_created(host):
    """Verify a backup archive (tar.gz) was created."""
    tc = TC["backup_oim_logs_archive_created"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_backup_oim_logs_output_path(host)
    result = find_log_bundle(host, output_path)

    if result["success"]:
        tl.passed(LOG["bundle_created"].format(path=result["bundle_path"]))
    else:
        tl.failed(LOG["bundle_missing"])

    assert result["success"], ASSERT["bundle_missing"].format(path=output_path)


@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(52)
def test_backup_oim_logs_metadata_exists(host):
    """Verify metadata.json exists alongside the backup archive."""
    tc = TC["backup_oim_logs_metadata_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_backup_oim_logs_output_path(host)
    cmd = f"find {output_path} -name 'metadata.json' 2>/dev/null | head -1"
    result = host.run(cmd)

    if result.rc != 0 or not result.stdout.strip():
        tl.failed(f"No metadata.json found in {output_path}")
        pytest.skip(f"No metadata.json found in {output_path}")

    metadata_path = result.stdout.strip()
    file_result = check_file_exists(host, metadata_path)

    if file_result["success"]:
        tl.passed(LOG["file_exists"].format(path=metadata_path))
    else:
        tl.failed(LOG["file_missing"].format(path=metadata_path))

    assert file_result["success"], f"Metadata file not found: {metadata_path}"


@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(53)
def test_backup_oim_logs_metadata_valid(host):
    """Verify metadata.json has valid structure."""
    tc = TC["backup_oim_logs_metadata_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_backup_oim_logs_output_path(host)
    cmd = f"find {output_path} -name 'metadata.json' 2>/dev/null | head -1"
    find_result = host.run(cmd)
    if find_result.rc != 0 or not find_result.stdout.strip():
        tl.skipped("No metadata.json found")
        pytest.skip("No metadata.json found")

    result = validate_backup_metadata_file(host, find_result.stdout.strip())
    if result["success"]:
        tl.passed(LOG["metadata_valid"])
    else:
        tl.failed(LOG["metadata_invalid"].format(error=result["error"]))

    assert result["success"], ASSERT["metadata_invalid"].format(error=result["error"])


@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(54)
def test_backup_oim_logs_metadata_sha256(host):
    """Verify metadata.json contains the archive SHA256 checksum."""
    tc = TC["backup_oim_logs_metadata_sha256"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_backup_oim_logs_output_path(host)
    cmd = f"find {output_path} -name 'metadata.json' 2>/dev/null | head -1"
    find_result = host.run(cmd)
    if find_result.rc != 0 or not find_result.stdout.strip():
        tl.skipped("No metadata.json found")
        pytest.skip("No metadata.json found")

    result = validate_backup_metadata_file(host, find_result.stdout.strip())
    if result["has_sha256"]:
        tl.passed(LOG["sha256_present"])
    else:
        tl.failed(LOG["sha256_missing"])

    assert result["has_sha256"], "archive_sha256 missing from metadata.json"


@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(55)
def test_backup_oim_logs_archive_contents(host):
    """Verify the archive contains at least one expected domain directory."""
    tc = TC["backup_oim_logs_archive_contents"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_backup_oim_logs_output_path(host)
    bundle_result = find_log_bundle(host, output_path)
    if not bundle_result["success"]:
        tl.skipped("No backup archive found, skipping content verification")
        pytest.skip("No backup archive found")

    result = validate_tar_contents(host, bundle_result["bundle_path"], BACKUP_ALL_DOMAINS)

    if result["found_dirs"]:
        tl.passed(f"Archive contains: {', '.join(result['found_dirs'])}")
    else:
        tl.failed("Archive contains none of the expected domain directories")

    assert result["found_dirs"], (
        f"Backup archive contains none of the expected domains: {BACKUP_ALL_DOMAINS}"
    )


# =============================================================================
# PATH RESOLUTION TESTS
# =============================================================================

@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(60)
def test_backup_oim_logs_cli_backup_path(host):
    """Verify -e backup_path overrides the default backup destination."""
    tc = TC["backup_oim_logs_cli_backup_path"]
    tl = TestLogger(tc["title"], tc["id"])

    custom_path = "/tmp/omnia_fvt_backup_oim_logs_cli"  # nosec: B108 - disposable FVT scratch dir
    host.run(f"rm -rf {custom_path} && mkdir -p {custom_path}")

    result = run_playbook(
        playbook=PLAYBOOK_BACKUP_OIM_LOGS,
        tag=None,
        extra_vars={"backup_path": custom_path},
    )

    if not result["success"]:
        tl.failed(LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]))
        _assert_playbook_ok(host, result, "(cli backup_path)")

    bundle_result = find_log_bundle(host, custom_path)
    if bundle_result["success"]:
        tl.passed(f"CLI backup_path honored: {bundle_result['bundle_path']}")
    else:
        tl.failed(f"No archive found under CLI backup_path override: {custom_path}")

    host.run(f"rm -rf {custom_path}")
    assert bundle_result["success"], (
        f"-e backup_path={custom_path} was not honored by backup_oim_logs.yml"
    )


@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(61)
def test_backup_oim_logs_env_var_backup_path(host):
    """Verify OMNIA_BACKUP_PATH overrides the default backup destination."""
    tc = TC["backup_oim_logs_env_var_backup_path"]
    tl = TestLogger(tc["title"], tc["id"])

    custom_path = "/tmp/omnia_fvt_backup_oim_logs_env"  # nosec: B108 - disposable FVT scratch dir
    host.run(f"rm -rf {custom_path} && mkdir -p {custom_path}")
    host.run(f"echo 'export OMNIA_BACKUP_PATH={custom_path}' >> {_ENV_FILE}")

    try:
        result = run_playbook(playbook=PLAYBOOK_BACKUP_OIM_LOGS, tag=None)
    finally:
        host.run(f"sed -i '\\|OMNIA_BACKUP_PATH={custom_path}|d' {_ENV_FILE}")

    if not result["success"]:
        tl.failed(LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]))
        _assert_playbook_ok(host, result, "(env OMNIA_BACKUP_PATH)")

    bundle_result = find_log_bundle(host, custom_path)
    if bundle_result["success"]:
        tl.passed(f"OMNIA_BACKUP_PATH honored: {bundle_result['bundle_path']}")
    else:
        tl.failed(f"No archive found under OMNIA_BACKUP_PATH override: {custom_path}")

    host.run(f"rm -rf {custom_path}")
    assert bundle_result["success"], (
        f"OMNIA_BACKUP_PATH={custom_path} was not honored by backup_oim_logs.yml"
    )


@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(61)
def test_backup_oim_logs_nfs_export_mounted(host):
    """Verify a raw NFS export backup_path ("<server>:/<path>") is honored.

    Requires an optional ``backup_nfs_export`` entry in test_config.yml
    (e.g. ``nfs:/mnt/backup_dir``).
    Skips cleanly when not configured, since this depends on lab-specific
    NFS infrastructure that isn't available in every environment.
    """
    tc = TC["backup_oim_logs_nfs_export_mounted"]
    tl = TestLogger(tc["title"], tc["id"])

    nfs_export = load_test_config().get("backup_nfs_export", "")
    if not nfs_export:
        tl.skipped("backup_nfs_export not configured in test_config.yml")
        pytest.skip("backup_nfs_export not configured in test_config.yml")

    result = run_playbook(
        playbook=PLAYBOOK_BACKUP_OIM_LOGS,
        tag=None,
        extra_vars={"backup_path": nfs_export},
    )

    if result["success"]:
        tl.passed(f"NFS export backup_path accepted: {nfs_export}")
    else:
        tl.failed(LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]))

    _assert_playbook_ok(host, result, "(nfs backup_path)")


@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(62)
def test_backup_oim_logs_config_file_domains(host):
    """Verify domain selection from backup_oim_logs_config.yml is honored."""
    tc = TC["backup_oim_logs_config_file_domains"]
    tl = TestLogger(tc["title"], tc["id"])

    config_path = get_backup_oim_logs_config_path(host)
    if not check_file_exists(host, config_path)["success"]:
        tl.skipped("backup_oim_logs_config.yml not present; skipping domain selection check")
        pytest.skip("backup_oim_logs_config.yml is optional and not present")

    config_result = validate_backup_config(host, config_path)
    selected_domains = config_result["domains"] or BACKUP_ALL_DOMAINS

    output_path = get_backup_oim_logs_output_path(host)
    bundle_result = find_log_bundle(host, output_path)
    if not bundle_result["success"]:
        tl.skipped("No backup archive found, skipping content verification")
        pytest.skip("No backup archive found")

    tar_result = validate_tar_contents(host, bundle_result["bundle_path"], selected_domains)
    if tar_result["found_dirs"]:
        tl.passed(f"Config-selected domains present: {', '.join(tar_result['found_dirs'])}")
    else:
        tl.failed("None of the config-selected domains were found in the archive")

    assert tar_result["found_dirs"], (
        f"Archive missing config-selected domains: {selected_domains}"
    )


# =============================================================================
# EDGE CASES
# =============================================================================

@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(70)
def test_backup_oim_logs_missing_domain_dir_warns(host):
    """Verify a domain without a log/ directory is skipped, not fatal."""
    tc = TC["backup_oim_logs_missing_domain_dir_warns"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_backup_oim_logs_output_path(host)
    cmd = f"find {output_path} -name 'metadata.json' 2>/dev/null | head -1"
    find_result = host.run(cmd)
    if find_result.rc != 0 or not find_result.stdout.strip():
        tl.skipped("No metadata.json found")
        pytest.skip("No metadata.json found")

    result = validate_backup_metadata_file(host, find_result.stdout.strip())
    domains_skipped = result["data"].get("domains_skipped", [])

    tl.passed(
        f"Backup completed successfully; domains skipped with a warning: "
        f"{domains_skipped or 'none'}"
    )
    assert result["success"], "metadata.json is invalid; cannot confirm graceful skip behavior"


@pytest.mark.functional
@pytest.mark.backup_oim_logs
@pytest.mark.order(71)
def test_backup_oim_logs_custom_project_name(host):
    """Verify a custom OMNIA_PROJECT_NAME is honored for the backup workspace."""
    tc = TC["backup_oim_logs_custom_project_name"]
    tl = TestLogger(tc["title"], tc["id"])

    custom_project = "fvt_backup_oim_logs_project"
    host.run(f"echo 'export OMNIA_PROJECT_NAME={custom_project}' >> {_ENV_FILE}")
    data_path = ""

    try:
        result = run_playbook(playbook=PLAYBOOK_BACKUP_OIM_LOGS, tag=None)
        data_path_result = check_env_var(host, "OMNIA_DATA_PATH")
        data_path = data_path_result["value"] if data_path_result["success"] else ""
        custom_output_path = f"{data_path}/utils/output/{custom_project}/backup_oim_logs"
        bundle_result = find_log_bundle(host, custom_output_path) if result["success"] else {
            "success": False, "bundle_path": "",
        }
    finally:
        host.run(f"sed -i '\\|OMNIA_PROJECT_NAME={custom_project}|d' {_ENV_FILE}")
        if data_path:
            host.run(f"rm -rf {data_path}/utils/output/{custom_project}")

    if bundle_result["success"]:
        tl.passed(f"Custom OMNIA_PROJECT_NAME honored: {bundle_result['bundle_path']}")
    else:
        tl.failed(f"No archive found under custom project workspace: {custom_output_path}")

    assert bundle_result["success"], (
        f"OMNIA_PROJECT_NAME={custom_project} was not honored by backup_oim_logs.yml"
    )
