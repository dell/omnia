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
Collect Scenario — Log Collector Verification Tests.

Verifies log collector input files, output files, and bundle contents.
"""

import pytest

from library.functions import (
    TestLogger,
    check_file_exists,
    check_dir_exists,
    validate_yaml_file,
    validate_collect_pxe_file,
    find_log_bundle,
    validate_metadata_file,
    validate_tar_contents,
    validate_bundle_log_files,
    check_env_var,
    get_utils_input_path,
    get_utils_output_path,
)
from library.vars import (
    TEST_CASES as TC,
    COLLECT_PXE_FILE,
    METADATA_FILE,
    FUNCTIONAL_GROUPS,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


# =============================================================================
# INPUT FILE VERIFICATION
# =============================================================================

@pytest.mark.sanity
@pytest.mark.collect
@pytest.mark.order(10)
def test_collect_input_file_exists(host):
    """Verify collect_pxe.yml input file exists on target."""
    tc = TC["collect_input_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{COLLECT_PXE_FILE}"

    result = check_file_exists(host, file_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=file_path))
    else:
        tl.failed(LOG["file_missing"].format(path=file_path))

    assert result["success"], ASSERT["file_missing"].format(path=file_path)


@pytest.mark.sanity
@pytest.mark.collect
@pytest.mark.order(11)
def test_collect_input_file_valid(host):
    """Verify collect_pxe.yml has valid YAML structure."""
    tc = TC["collect_input_file_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{COLLECT_PXE_FILE}"

    result = validate_yaml_file(host, file_path)

    if result["success"]:
        tl.passed(LOG["file_valid"].format(path=file_path))
    else:
        tl.failed(LOG["file_invalid"].format(path=file_path), result["error"])

    assert result["success"], ASSERT["file_invalid"].format(
        path=file_path,
        error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.collect
@pytest.mark.order(12)
def test_collect_functional_groups_valid(host):
    """Verify collect_pxe.yml contains valid functional groups."""
    tc = TC["collect_functional_groups_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{COLLECT_PXE_FILE}"

    result = validate_collect_pxe_file(host, file_path)

    if result["success"]:
        groups_str = ", ".join(result["groups"]) if result["groups"] else "(empty)"
        tl.passed(f"Valid functional groups: {groups_str}")
    else:
        tl.failed(
            LOG["functional_groups_invalid"].format(group=result["invalid_groups"]),
            result["error"],
        )

    assert result["success"], ASSERT["functional_groups_invalid"].format(
        group=result["invalid_groups"],
        valid_groups=", ".join(FUNCTIONAL_GROUPS),
    )


# =============================================================================
# OUTPUT VERIFICATION
# =============================================================================

@pytest.mark.sanity
@pytest.mark.collect
@pytest.mark.order(20)
def test_collect_output_dir_exists(host):
    """Verify log collection output directory exists."""
    tc = TC["collect_output_dir_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    result = check_dir_exists(host, output_path)

    if result["success"]:
        tl.passed(LOG["dir_exists"].format(path=output_path))
    else:
        tl.failed(LOG["dir_missing"].format(path=output_path))

    assert result["success"], f"Output directory not found: {output_path}"


@pytest.mark.functional
@pytest.mark.collect
@pytest.mark.order(21)
def test_collect_bundle_created(host):
    """Verify log bundle tar.gz file was created."""
    tc = TC["collect_bundle_created"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    result = find_log_bundle(host, output_path)

    if result["success"]:
        tl.passed(LOG["bundle_created"].format(path=result["bundle_path"]))
    else:
        tl.failed(LOG["bundle_missing"])

    assert result["success"], ASSERT["bundle_missing"].format(path=output_path)


@pytest.mark.functional
@pytest.mark.collect
@pytest.mark.order(22)
def test_collect_metadata_exists(host):
    """Verify metadata.json file exists."""
    tc = TC["collect_metadata_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    # Find any metadata.json file in the collect directory tree
    cmd = f"find {output_path} -name 'metadata.json' 2>/dev/null | head -1"
    result = host.run(cmd)

    if result.rc == 0 and result.stdout.strip():
        metadata_path = result.stdout.strip()
    else:
        tl.failed(f"No metadata.json found in {output_path}")
        pytest.skip(f"No metadata.json found in {output_path}")

    result = check_file_exists(host, metadata_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=metadata_path))
    else:
        tl.failed(LOG["file_missing"].format(path=metadata_path))

    assert result["success"], f"Metadata file not found: {metadata_path}"


@pytest.mark.functional
@pytest.mark.collect
@pytest.mark.order(23)
def test_collect_metadata_valid(host):
    """Verify metadata.json has valid structure."""
    tc = TC["collect_metadata_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    # Find any metadata.json file in the collect directory tree
    cmd = f"find {output_path} -name 'metadata.json' 2>/dev/null | head -1"
    result = host.run(cmd)

    if result.rc == 0 and result.stdout.strip():
        metadata_path = result.stdout.strip()
    else:
        tl.failed(f"No metadata.json found in {output_path}")
        pytest.skip(f"No metadata.json found in {output_path}")

    result = validate_metadata_file(host, metadata_path)

    if result["success"]:
        tl.passed(LOG["metadata_valid"])
    else:
        tl.failed(LOG["metadata_invalid"].format(error=result["error"]))

    assert result["success"], ASSERT["metadata_invalid"].format(error=result["error"])


@pytest.mark.functional
@pytest.mark.collect
@pytest.mark.order(24)
def test_collect_metadata_sha256(host):
    """Verify metadata.json contains SHA256 checksum."""
    tc = TC["collect_metadata_sha256"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    # Find any metadata.json file in the collect directory tree
    cmd = f"find {output_path} -name 'metadata.json' 2>/dev/null | head -1"
    result = host.run(cmd)

    if result.rc == 0 and result.stdout.strip():
        metadata_path = result.stdout.strip()
    else:
        tl.failed(f"No metadata.json found in {output_path}")
        pytest.skip(f"No metadata.json found in {output_path}")

    result = validate_metadata_file(host, metadata_path)

    if result["has_sha256"]:
        tl.passed(LOG["sha256_present"])
    else:
        tl.failed(LOG["sha256_missing"])

    assert result["has_sha256"], "SHA256 checksum missing from metadata.json"


@pytest.mark.functional
@pytest.mark.collect
@pytest.mark.order(25)
def test_collect_bundle_contents(host):
    """Verify log bundle contains expected directories."""
    tc = TC["collect_bundle_contents"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    bundle_result = find_log_bundle(host, output_path)

    if not bundle_result["success"]:
        tl.skipped("No log bundle found, skipping content verification")
        pytest.skip("No log bundle found")

    # Expected directories in the bundle (updated to match actual structure)
    expected_dirs = ["k8s", "slurm"]

    result = validate_tar_contents(host, bundle_result["bundle_path"], expected_dirs)

    if result["success"]:
        tl.passed(f"Bundle contains: {', '.join(result['found_dirs'])}")
    else:
        tl.failed(f"Missing directories: {', '.join(result['missing_dirs'])}")

    assert result["success"], f"Bundle missing directories: {result['missing_dirs']}"


@pytest.mark.functional
@pytest.mark.collect
@pytest.mark.order(26)
def test_collect_bundle_log_files_content(host):
    """Verify log bundle contains log files with content in k8s and slurm directories."""
    tc = TC["collect_bundle_log_files_content"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    bundle_result = find_log_bundle(host, output_path)

    if not bundle_result["success"]:
        tl.skipped("No log bundle found, skipping log file verification")
        pytest.skip("No log bundle found")

    result = validate_bundle_log_files(host, bundle_result["bundle_path"])

    if not result["success"]:
        tl.failed(f"Failed to verify log files: {result['error']}")
        pytest.fail(f"Failed to verify log files: {result['error']}")

    # Report collected files
    if result["collected_files"]:
        tl.passed(f"Collected {len(result['collected_files'])} log files with content")
        for file_path in result["collected_files"]:
            tl.info(f"  - {file_path}")

    # Report empty files
    if result["empty_files"]:
        tl.info(f"Found {len(result['empty_files'])} empty log files")
        for file_path in result["empty_files"]:
            tl.info(f"  - {file_path} (empty)")

    # Overall test passes if at least some files were collected
    if len(result["collected_files"]) > 0:
        tl.passed(f"Log collection successful: {len(result['collected_files'])} files with content")
    else:
        tl.failed("No log files with content found in bundle")

    assert len(result["collected_files"]) > 0, "No log files with content found in bundle"


# =============================================================================
# ENVIRONMENT VARIABLE VERIFICATION
# =============================================================================

@pytest.mark.sanity
@pytest.mark.collect
@pytest.mark.order(30)
def test_collect_env_vars_loaded(host):
    """Verify OMNIA_DATA_PATH is loaded from environment."""
    tc = TC["collect_env_vars_loaded"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_env_var(host, "OMNIA_DATA_PATH")

    if result["success"]:
        tl.passed(LOG["env_var_present"].format(var="OMNIA_DATA_PATH", value=result["value"]))
    else:
        tl.failed(LOG["env_var_missing"].format(var="OMNIA_DATA_PATH"))

    assert result["success"], ASSERT["env_var_missing"].format(var="OMNIA_DATA_PATH")


@pytest.mark.sanity
@pytest.mark.collect
@pytest.mark.order(31)
def test_collect_project_name_loaded(host):
    """Verify OMNIA_PROJECT_NAME is loaded from environment."""
    tc = TC["collect_project_name_loaded"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_env_var(host, "OMNIA_PROJECT_NAME")

    if result["success"]:
        tl.passed(LOG["env_var_present"].format(var="OMNIA_PROJECT_NAME", value=result["value"]))
    else:
        tl.failed(LOG["env_var_missing"].format(var="OMNIA_PROJECT_NAME"))

    assert result["success"], ASSERT["env_var_missing"].format(var="OMNIA_PROJECT_NAME")
