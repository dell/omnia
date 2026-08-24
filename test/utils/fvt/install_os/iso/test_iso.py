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
    validate_iso_config,
    validate_os_install_credentials,
    find_custom_iso,
    verify_iso_checksum,
    verify_kickstart_in_iso,
    get_utils_input_path,
    get_utils_output_path,
)
from library.vars import (
    TEST_CASES as TC,
    ISO_CONFIG_FILE,
    OS_INSTALL_CREDENTIALS_FILE,
    ISO_OUTPUT_DIR,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


# =============================================================================
# INPUT FILE VERIFICATION
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(10)
def test_install_os_config_file_exists(host):
    """Verify iso_config.yml exists on target."""
    tc = TC["install_os_config_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{ISO_CONFIG_FILE}"

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
    """Verify iso_config.yml has valid structure."""
    tc = TC["install_os_config_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{ISO_CONFIG_FILE}"

    # Check if file exists first
    exists_result = check_file_exists(host, file_path)
    if not exists_result["success"]:
        tl.skipped("Config file not found, skipping validation")
        pytest.skip("Config file not found")

    result = validate_iso_config(host, file_path)

    if result["success"]:
        tl.passed(LOG["iso_config_valid"])
    else:
        tl.failed(LOG["iso_config_invalid"].format(error=result["error"]))

    assert result["success"], ASSERT["iso_config_invalid"].format(error=result["error"])


@pytest.mark.sanity
@pytest.mark.order(12)
def test_install_os_credentials_file_exists(host):
    """Verify os_install_credentials.yml exists."""
    tc = TC["install_os_credentials_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{OS_INSTALL_CREDENTIALS_FILE}"

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
    """Verify ISO output directory exists."""
    tc = TC["install_os_output_dir_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_dir_exists(host, ISO_OUTPUT_DIR)

    if result["success"]:
        tl.passed(LOG["dir_exists"].format(path=ISO_OUTPUT_DIR))
    else:
        tl.failed(LOG["dir_missing"].format(path=ISO_OUTPUT_DIR))

    assert result["success"], f"Output directory not found: {ISO_OUTPUT_DIR}"


@pytest.mark.functional
@pytest.mark.order(21)
def test_install_os_custom_iso_created(host):
    """Verify custom ISO with Kickstart was created."""
    tc = TC["install_os_custom_iso_created"]
    tl = TestLogger(tc["title"], tc["id"])

    result = find_custom_iso(host, ISO_OUTPUT_DIR)

    if result["success"]:
        tl.passed(LOG["custom_iso_created"].format(path=result["iso_path"]))
    else:
        tl.skipped("Custom ISO not found (may not have been created yet)")
        pytest.skip("Custom ISO not found")


@pytest.mark.functional
@pytest.mark.order(22)
def test_install_os_iso_checksum_valid(host):
    """Verify ISO checksum matches expected value."""
    tc = TC["install_os_iso_checksum_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    # First find the custom ISO
    iso_result = find_custom_iso(host, ISO_OUTPUT_DIR)
    if not iso_result["success"]:
        tl.skipped("Custom ISO not found, skipping checksum verification")
        pytest.skip("Custom ISO not found")

    # Get expected checksum from config
    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/{ISO_CONFIG_FILE}"
    from library.functions import validate_yaml_file

    config_result = validate_yaml_file(host, config_path)
    if not config_result["success"]:
        tl.skipped("Cannot read config for expected checksum")
        pytest.skip("Cannot read config for expected checksum")

    expected_checksum = config_result["data"].get("iso_source_checksum", "")
    if not expected_checksum:
        tl.skipped("No expected checksum in config")
        pytest.skip("No expected checksum in config")

    result = verify_iso_checksum(host, iso_result["iso_path"], expected_checksum)

    if result["success"]:
        tl.passed(LOG["iso_checksum_valid"])
    else:
        tl.failed(
            LOG["iso_checksum_invalid"].format(
                expected=expected_checksum,
                actual=result["actual_checksum"],
            )
        )

    assert result["success"], ASSERT["iso_checksum_invalid"].format(
        expected=expected_checksum,
        actual=result["actual_checksum"],
    )


@pytest.mark.functional
@pytest.mark.order(23)
def test_install_os_kickstart_injected(host):
    """Verify Kickstart configuration is injected into ISO."""
    tc = TC["install_os_kickstart_injected"]
    tl = TestLogger(tc["title"], tc["id"])

    # First find the custom ISO
    iso_result = find_custom_iso(host, ISO_OUTPUT_DIR)
    if not iso_result["success"]:
        tl.skipped("Custom ISO not found, skipping kickstart verification")
        pytest.skip("Custom ISO not found")

    result = verify_kickstart_in_iso(host, iso_result["iso_path"])

    if result["success"] and result["found"]:
        tl.passed(LOG["kickstart_injected"])
    elif result["success"] and not result["found"]:
        tl.failed(LOG["kickstart_missing"])
    else:
        tl.failed(result["error"])

    assert result["success"] and result["found"], ASSERT["kickstart_missing"]
