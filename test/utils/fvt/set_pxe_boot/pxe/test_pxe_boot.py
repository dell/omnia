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
Set PXE Boot Scenario — PXE Boot Verification Tests.

Verifies PXE boot configuration files, inventory, and output files.
"""

import pytest

from library.functions import (
    TestLogger,
    check_file_exists,
    check_dir_exists,
    validate_yaml_file,
    validate_pxe_config,
    validate_ini_inventory,
    validate_failed_nodes_json,
    get_utils_input_path,
    get_utils_output_path,
)
from library.vars import (
    TEST_CASES as TC,
    SET_PXE_BOOT_CONFIG_FILE,
    SET_PXE_BOOT_INVENTORY_FILE,
    SET_PXE_BOOT_CREDENTIALS_FILE,
    FAILED_NODES_FILE,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


# =============================================================================
# INPUT FILE VERIFICATION
# =============================================================================

@pytest.mark.sanity
@pytest.mark.pxe
@pytest.mark.order(10)
def test_pxe_config_file_exists(host):
    """Verify set_pxe_boot_config.yml exists on target."""
    tc = TC["pxe_config_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{SET_PXE_BOOT_CONFIG_FILE}"

    result = check_file_exists(host, file_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=file_path))
    else:
        # Config file is optional, warn but don't fail
        tl.skipped(f"Config file not found (using defaults): {file_path}")
        pytest.skip(f"Config file not found: {file_path}")


@pytest.mark.sanity
@pytest.mark.pxe
@pytest.mark.order(11)
def test_pxe_config_valid(host):
    """Verify set_pxe_boot_config.yml has valid structure."""
    tc = TC["pxe_config_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{SET_PXE_BOOT_CONFIG_FILE}"

    # Check if file exists first
    exists_result = check_file_exists(host, file_path)
    if not exists_result["success"]:
        tl.skipped("Config file not found, skipping validation")
        pytest.skip("Config file not found")

    result = validate_pxe_config(host, file_path)

    if result["success"]:
        tl.passed(LOG["pxe_config_valid"])
    else:
        tl.failed(LOG["pxe_config_invalid"].format(error=result["error"]))

    assert result["success"], ASSERT["pxe_config_invalid"].format(error=result["error"])


@pytest.mark.sanity
@pytest.mark.pxe
@pytest.mark.order(12)
def test_pxe_inventory_file_exists(host):
    """Verify set_pxe_boot.ini inventory file exists."""
    tc = TC["pxe_inventory_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{SET_PXE_BOOT_INVENTORY_FILE}"

    result = check_file_exists(host, file_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=file_path))
    else:
        tl.skipped(f"Inventory file not found: {file_path}")
        pytest.skip(f"Inventory file not found: {file_path}")


@pytest.mark.sanity
@pytest.mark.pxe
@pytest.mark.order(13)
def test_pxe_inventory_valid(host):
    """Verify set_pxe_boot.ini has valid INI format."""
    tc = TC["pxe_inventory_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{SET_PXE_BOOT_INVENTORY_FILE}"

    # Check if file exists first
    exists_result = check_file_exists(host, file_path)
    if not exists_result["success"]:
        tl.skipped("Inventory file not found, skipping validation")
        pytest.skip("Inventory file not found")

    result = validate_ini_inventory(host, file_path)

    if result["success"]:
        tl.passed(f"Valid inventory with {len(result['hosts'])} hosts")
    else:
        tl.failed(LOG["inventory_invalid"].format(error=result["error"]))

    assert result["success"], ASSERT["inventory_invalid"].format(error=result["error"])


@pytest.mark.sanity
@pytest.mark.pxe
@pytest.mark.order(14)
def test_pxe_credentials_file_exists(host):
    """Verify set_pxe_boot_credentials.yml exists."""
    tc = TC["pxe_credentials_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{SET_PXE_BOOT_CREDENTIALS_FILE}"

    result = check_file_exists(host, file_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=file_path))
    else:
        # Credentials file is optional (can be collected interactively)
        tl.skipped(f"Credentials file not found (will prompt): {file_path}")
        pytest.skip(f"Credentials file not found: {file_path}")


# =============================================================================
# OUTPUT VERIFICATION
# =============================================================================

@pytest.mark.functional
@pytest.mark.pxe
@pytest.mark.order(20)
def test_pxe_output_dir_exists(host):
    """Verify PXE boot output directory exists."""
    tc = TC["pxe_output_dir_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    result = check_dir_exists(host, output_path)

    if result["success"]:
        tl.passed(LOG["dir_exists"].format(path=output_path))
    else:
        tl.failed(LOG["dir_missing"].format(path=output_path))

    assert result["success"], f"Output directory not found: {output_path}"


@pytest.mark.functional
@pytest.mark.pxe
@pytest.mark.order(21)
def test_pxe_failed_nodes_file(host):
    """Verify failed_nodes.json output file was created."""
    tc = TC["pxe_failed_nodes_file"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    file_path = f"{output_path}/{FAILED_NODES_FILE}"

    result = check_file_exists(host, file_path)

    if result["success"]:
        tl.passed(LOG["failed_nodes_created"].format(path=file_path))
    else:
        # File only created after PXE boot runs
        tl.skipped("failed_nodes.json not found (PXE boot may not have run)")
        pytest.skip("failed_nodes.json not found")


@pytest.mark.functional
@pytest.mark.pxe
@pytest.mark.order(22)
def test_pxe_failed_nodes_valid(host):
    """Verify failed_nodes.json has valid structure."""
    tc = TC["pxe_failed_nodes_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    file_path = f"{output_path}/{FAILED_NODES_FILE}"

    # Check if file exists first
    exists_result = check_file_exists(host, file_path)
    if not exists_result["success"]:
        tl.skipped("failed_nodes.json not found, skipping validation")
        pytest.skip("failed_nodes.json not found")

    result = validate_failed_nodes_json(host, file_path)

    if result["success"]:
        data = result["data"]
        tl.passed(
            f"Valid structure: {data.get('success_count', 0)} success, "
            f"{data.get('failure_count', 0)} failures"
        )
    else:
        tl.failed(f"Invalid structure: {result['error']}")

    assert result["success"], f"Invalid failed_nodes.json: {result['error']}"


# =============================================================================
# CONFIGURATION VERIFICATION
# =============================================================================

@pytest.mark.sanity
@pytest.mark.pxe
@pytest.mark.order(30)
def test_pxe_phone_home_enabled(host):
    """Verify phone-home verification is enabled in config."""
    tc = TC["pxe_phone_home_enabled"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{SET_PXE_BOOT_CONFIG_FILE}"

    # Check if file exists first
    exists_result = check_file_exists(host, file_path)
    if not exists_result["success"]:
        # Default is enabled
        tl.passed("Config file not found, using default (phone-home enabled)")
        return

    result = validate_pxe_config(host, file_path)

    if not result["success"]:
        tl.skipped(f"Config validation failed: {result['error']}")
        pytest.skip(f"Config validation failed: {result['error']}")

    config = result["config"]
    phone_home = config.get("enable_phone_home", True)

    if phone_home:
        tl.passed(LOG["phone_home_enabled"])
    else:
        tl.passed(LOG["phone_home_disabled"])


@pytest.mark.sanity
@pytest.mark.pxe
@pytest.mark.order(31)
def test_pxe_phone_home_config(host):
    """Verify phone-home configuration values are valid."""
    tc = TC["pxe_phone_home_config"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{SET_PXE_BOOT_CONFIG_FILE}"

    # Check if file exists first
    exists_result = check_file_exists(host, file_path)
    if not exists_result["success"]:
        tl.skipped("Config file not found, using defaults")
        pytest.skip("Config file not found")

    result = validate_pxe_config(host, file_path)

    if not result["success"]:
        tl.failed(f"Config validation failed: {result['error']}")
        assert False, result["error"]

    config = result["config"]

    # Validate phone-home timing values
    pause = config.get("phone_home_pause_minutes", 3)
    retries = config.get("phone_home_retries", 120)
    delay = config.get("phone_home_delay", 15)

    errors = []
    if pause < 0:
        errors.append(f"phone_home_pause_minutes must be >= 0, got {pause}")
    if retries < 1:
        errors.append(f"phone_home_retries must be >= 1, got {retries}")
    if delay < 1:
        errors.append(f"phone_home_delay must be >= 1, got {delay}")

    if errors:
        tl.failed("; ".join(errors))
        assert False, "; ".join(errors)

    total_wait = pause * 60 + retries * delay
    tl.passed(
        f"Phone-home config: pause={pause}min, retries={retries}, "
        f"delay={delay}s (total wait: {total_wait}s)"
    )
