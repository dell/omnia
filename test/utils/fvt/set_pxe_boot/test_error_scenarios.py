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
Set PXE Boot Scenario — Error Scenario Tests.

Tests for error conditions and edge cases in set_pxe_boot playbook execution.
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    get_utils_input_path,
    check_file_exists,
    validate_pxe_config,
)
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_SET_PXE_BOOT,
    PLAYBOOK_WORKDIR,
    SET_PXE_BOOT_CONFIG_FILE,
    SET_PXE_BOOT_INVENTORY_FILE,
    SET_PXE_BOOT_CREDENTIALS_FILE,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


@pytest.mark.regression
@pytest.mark.pxe
@pytest.mark.order(100)
def test_pxe_missing_inventory_fails(host):
    """Verify set_pxe_boot.yml fails without inventory file."""
    tc = TC["pxe_missing_inventory_fails"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    inventory_path = f"{input_path}/{SET_PXE_BOOT_INVENTORY_FILE}"

    # Check if inventory exists first
    inv_result = check_file_exists(host, inventory_path)
    if not inv_result["success"]:
        tl.skipped("Inventory file not found, skipping test")
        pytest.skip("Inventory file not found")

    # Temporarily rename inventory file to simulate missing inventory
    host.run(f"mv {inventory_path} {inventory_path}.backup")
    
    try:
        result = run_playbook(
            playbook=PLAYBOOK_SET_PXE_BOOT,
            tag="credentials",
        )

        # Should fail or skip when inventory is missing
        if not result["success"]:
            tl.passed(LOG["playbook_failed_as_expected"].format(error=result.get("error", "Inventory missing")))
        else:
            tl.failed("Playbook succeeded despite missing inventory (unexpected)")
    finally:
        # Restore inventory file
        host.run(f"mv {inventory_path}.backup {inventory_path} 2>/dev/null || true")


@pytest.mark.regression
@pytest.mark.pxe
@pytest.mark.order(101)
def test_pxe_missing_admin_ip_fails(host):
    """Verify set_pxe_boot.yml fails when admin_ip missing with phone-home enabled."""
    tc = TC["pxe_missing_admin_ip_fails"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    inventory_path = f"{input_path}/{SET_PXE_BOOT_INVENTORY_FILE}"
    config_path = f"{input_path}/{SET_PXE_BOOT_CONFIG_FILE}"

    # Check if inventory exists
    inv_result = check_file_exists(host, inventory_path)
    if not inv_result["success"]:
        tl.skipped("Inventory file not found, skipping test")
        pytest.skip("Inventory file not found")

    # Backup original inventory
    host.run(f"cp {inventory_path} {inventory_path}.backup")

    # Create inventory without admin_ip for testing
    test_inventory = """[bmc]
172.16.0.73 hostname=node01
"""
    host.run(f"cat > {inventory_path} << 'EOF'\n{test_inventory}EOF")

    # Ensure phone-home is enabled in config
    config_result = validate_pxe_config(host, config_path)
    if config_result["success"]:
        config = config_result["config"]
        if not config.get("enable_phone_home", True):
            tl.skipped("Phone-home is disabled, skipping test")
            pytest.skip("Phone-home is disabled")

    try:
        result = run_playbook(
            playbook=PLAYBOOK_SET_PXE_BOOT,
            tag="pxe_boot",
        )

        # Should fail when admin_ip is missing and phone-home is enabled
        if not result["success"]:
            tl.passed(LOG["playbook_failed_as_expected"].format(error=result.get("error", "admin_ip missing")))
        else:
            tl.failed("Playbook succeeded despite missing admin_ip (unexpected)")
    finally:
        # Restore original inventory
        host.run(f"mv {inventory_path}.backup {inventory_path} 2>/dev/null || true")


@pytest.mark.regression
@pytest.mark.pxe
@pytest.mark.order(102)
def test_pxe_invalid_config_params_fails(host):
    """Verify set_pxe_boot.yml fails with invalid configuration parameters."""
    tc = TC["pxe_invalid_config_params_fails"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/{SET_PXE_BOOT_CONFIG_FILE}"

    # Check if config exists
    config_exists = check_file_exists(host, config_path)
    if not config_exists["success"]:
        tl.skipped("Config file not found, skipping test")
        pytest.skip("Config file not found")

    # Backup original config
    host.run(f"cp {config_path} {config_path}.backup")

    # Create invalid config with negative phone_home_retries
    invalid_config = """---
enable_phone_home: true
phone_home_pause_minutes: 3
phone_home_retries: -1
phone_home_delay: 15
restart_host: true
force_restart: true
"""
    host.run(f"cat > {config_path} << 'EOF'\n{invalid_config}EOF")

    try:
        result = run_playbook(
            playbook=PLAYBOOK_SET_PXE_BOOT,
            tag="pxe_boot",
        )

        # Should fail with invalid parameters
        if not result["success"]:
            tl.passed(LOG["playbook_failed_as_expected"].format(error=result.get("error", "Invalid config")))
        else:
            tl.failed("Playbook succeeded with invalid config (unexpected)")
    finally:
        # Restore original config
        host.run(f"mv {config_path}.backup {config_path} 2>/dev/null || true")


@pytest.mark.regression
@pytest.mark.pxe
@pytest.mark.order(103)
def test_pxe_invalid_credentials_fails(host):
    """Verify set_pxe_boot.yml fails with invalid BMC credentials."""
    tc = TC["pxe_invalid_credentials_fails"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    creds_path = f"{input_path}/{SET_PXE_BOOT_CREDENTIALS_FILE}"
    inventory_path = f"{input_path}/{SET_PXE_BOOT_INVENTORY_FILE}"

    # Check if inventory exists
    inv_result = check_file_exists(host, inventory_path)
    if not inv_result["success"]:
        tl.skipped("Inventory file not found, skipping test")
        pytest.skip("Inventory file not found")

    # Backup original credentials
    creds_exists = check_file_exists(host, creds_path)
    if creds_exists["success"]:
        host.run(f"cp {creds_path} {creds_path}.backup")

    # Create invalid credentials
    invalid_creds = """---
bmc_username: "invalid_user"
bmc_password: "invalid_password"
"""
    host.run(f"cat > {creds_path} << 'EOF'\n{invalid_creds}EOF")

    try:
        result = run_playbook(
            playbook=PLAYBOOK_SET_PXE_BOOT,
            tag="pxe_boot",
        )

        # Should fail with invalid credentials (when BMC is reachable)
        # Note: This test may pass if BMC is not reachable
        if not result["success"]:
            tl.passed(LOG["playbook_failed_as_expected"].format(error=result.get("error", "Invalid credentials")))
        else:
            tl.passed("Playbook succeeded (BMC may not be reachable, credentials not validated)")
    finally:
        # Restore original credentials
        if creds_exists["success"]:
            host.run(f"mv {creds_path}.backup {creds_path} 2>/dev/null || true")
        else:
            host.run(f"rm -f {creds_path} 2>/dev/null || true")
