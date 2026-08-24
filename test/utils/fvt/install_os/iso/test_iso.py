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
Install OS Scenario — ISO Verification Tests.

Verifies ISO configuration files, credentials, and output artifacts.
"""

import pytest

from library.functions import (
    TestLogger,
    check_file_exists,
    check_dir_exists,
    validate_yaml_file,
    validate_install_os_config,
    validate_install_os_credentials,
    find_custom_iso,
    verify_iso_checksum,
    verify_kickstart_in_iso,
    get_utils_input_path,
    get_utils_output_path,
)
from library.vars import (
    TEST_CASES as TC,
    INSTALL_OS_CONFIG_FILE,
    INSTALL_OS_CREDENTIALS_FILE,
    INSTALL_OS_STATUS_FILE,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


# =============================================================================
# INPUT FILE VERIFICATION
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(10)
def test_install_os_config_file_exists(host):
    """Verify install_os_config.yml exists on target."""
    tc = TC["install_os_config_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{INSTALL_OS_CONFIG_FILE}"

    result = check_file_exists(host, file_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=file_path))
    else:
        # Config file is optional for basic tests
        tl.skipped(f"Config file not found (optional): {file_path}")
        pytest.skip(f"Config file not found: {file_path}")


@pytest.mark.sanity
@pytest.mark.order(11)
def test_install_os_config_valid(host):
    """Verify install_os_config.yml has valid structure."""
    tc = TC["install_os_config_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{INSTALL_OS_CONFIG_FILE}"

    # Check if file exists first
    exists_result = check_file_exists(host, file_path)
    if not exists_result["success"]:
        tl.skipped("Config file not found, skipping validation")
        pytest.skip("Config file not found")

    result = validate_install_os_config(host, file_path)

    if result["success"]:
        tl.passed(LOG["iso_config_valid"])
    else:
        tl.failed(LOG["iso_config_invalid"].format(error=result["error"]))

    assert result["success"], ASSERT["iso_config_invalid"].format(error=result["error"])


@pytest.mark.sanity
@pytest.mark.order(12)
def test_install_os_credentials_file_exists(host):
    """Verify install_os_credentials.yml exists."""
    tc = TC["install_os_credentials_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{INSTALL_OS_CREDENTIALS_FILE}"

    result = check_file_exists(host, file_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=file_path))
    else:
        # Credentials file is optional (can be provided via extra-vars)
        tl.skipped(f"Credentials file not found (optional): {file_path}")
        pytest.skip(f"Credentials file not found: {file_path}")


# =============================================================================
# OUTPUT VERIFICATION
# =============================================================================

@pytest.mark.functional
@pytest.mark.order(20)
def test_install_os_output_dir_exists(host):
    """Verify install_os output directory exists."""
    tc = TC["install_os_output_dir_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    result = check_dir_exists(host, output_path)

    if result["success"]:
        tl.passed(LOG["dir_exists"].format(path=output_path))
    else:
        tl.failed(LOG["dir_missing"].format(path=output_path))

    assert result["success"], f"Output directory not found: {output_path}"


@pytest.mark.functional
@pytest.mark.order(21)
def test_install_os_status_file_exists(host):
    """Verify install_os_status.yml output file created."""
    tc = TC["install_os_status_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    status_path = f"{output_path}/{INSTALL_OS_STATUS_FILE}"

    result = check_file_exists(host, status_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=status_path))
    else:
        tl.skipped("install_os_status.yml not found (requires build_iso or deploy execution)")
        pytest.skip("install_os_status.yml not found")


@pytest.mark.functional
@pytest.mark.order(22)
def test_install_os_status_valid(host):
    """Verify install_os_status.yml has valid structure."""
    tc = TC["install_os_status_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    status_path = f"{output_path}/{INSTALL_OS_STATUS_FILE}"

    exists = check_file_exists(host, status_path)
    if not exists["success"]:
        tl.skipped("install_os_status.yml not found, skipping validation")
        pytest.skip("install_os_status.yml not found")

    yaml_result = validate_yaml_file(host, status_path)
    if not yaml_result["success"]:
        tl.failed(yaml_result["error"])
        pytest.fail(yaml_result["error"])

    data = yaml_result["data"]
    required = ["utility", "status", "timestamp"]
    missing = [k for k in required if k not in data]

    if missing:
        tl.failed(f"Missing keys in install_os_status.yml: {missing}")
    else:
        tl.passed("install_os_status.yml structure is valid")

    assert not missing, f"Missing keys in install_os_status.yml: {missing}"


@pytest.mark.functional
@pytest.mark.order(30)
def test_install_os_custom_iso_created(host):
    """Verify custom ISO created (optional).

    Custom ISO is typically written to an NFS path (custom_iso_path). This test
    only runs if the configured NFS share is mounted locally and the ISO is
    visible from the test host.
    """
    tc = TC["install_os_custom_iso_created"]
    tl = TestLogger(tc["title"], tc["id"])

    # Prefer checking output path itself; if ISO is not created here, skip.
    output_path = get_utils_output_path(host)
    result = find_custom_iso(host, output_path)

    if result["success"]:
        tl.passed(LOG["custom_iso_created"].format(path=result["iso_path"]))
    else:
        tl.skipped("Custom ISO not found in output directory (may be on NFS mount)")
        pytest.skip("Custom ISO not found")


@pytest.mark.functional
@pytest.mark.order(31)
def test_install_os_kickstart_generated(host):
    """Verify kickstart.ks generated (optional)."""
    tc = TC["install_os_kickstart_generated"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    ks_path = f"{output_path}/kickstart.ks"
    result = check_file_exists(host, ks_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=ks_path))
    else:
        tl.skipped("kickstart.ks not found in output directory (may be written to NFS path)")
        pytest.skip("kickstart.ks not found")
