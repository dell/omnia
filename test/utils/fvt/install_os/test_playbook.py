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
Install OS Scenario — Playbook Deployment Tests.

Tests for deploying the install_os.yml playbook with various tags.

Note: install_os.yml requires many parameters (ISO path, NFS path, BMC IP, credentials, etc.).
These tests validate the playbook wiring and non-interactive behavior.
Full end-to-end OS installation requires actual hardware and is out of scope.
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    load_test_config,
    get_utils_input_path,
)
from library.vars import TEST_CASES as TC, PLAYBOOK_INSTALL_OS, PLAYBOOK_WORKDIR
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_install_os_credentials(host):
    """Deploy install_os.yml with credentials tag.

    Validates credential collection and encryption. Requires proper config and credentials.
    """
    tc = TC["deploy_install_os_credentials"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-verification: Check credentials are configured
    from library.functions import load_test_credentials
    try:
        creds = load_test_credentials()
        has_creds = bool(creds.get("bmc_username") and creds.get("bmc_password") and creds.get("os_root_password"))
        if not has_creds:
            tl.skipped("Credentials not configured - run setup_env.sh --set-domain-creds")
            pytest.skip("Credentials not configured")
    except Exception as e:
        tl.failed(f"Failed to load credentials: {e}")
        pytest.fail(f"Failed to load credentials: {e}")

    result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="credentials")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
        return

    tl.failed(
        LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
        result.get("error", "See playbook output above"),
    )
    pytest.fail("install_os credentials tag failed")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(1)
def test_deploy_install_os_build_iso(host):
    """Deploy install_os.yml with build_iso tag.

    Validates ISO building with proper configuration. Requires source ISO and NFS path.
    """
    tc = TC["deploy_install_os_build_iso"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-verification: Check config has required parameters
    from library.functions import get_utils_input_path, validate_install_os_config
    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"

    config_result = validate_install_os_config(host, config_path)
    if not config_result["success"]:
        tl.failed(f"Config validation failed: {config_result['error']}")
        pytest.fail(f"Config validation failed: {config_result['error']}")

    config = config_result.get("config", {})

    # Check required parameters for build_iso
    source_iso = config.get("source_iso_path", "")
    custom_iso = config.get("custom_iso_path", "")

    if not source_iso:
        tl.skipped("source_iso_path not configured in install_os_config.yml")
        pytest.skip("source_iso_path not configured")

    if not custom_iso:
        tl.skipped("custom_iso_path not configured in install_os_config.yml")
        pytest.skip("custom_iso_path not configured")

    result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="build_iso")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
        return

    tl.failed(
        LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
        result.get("error", "See playbook output above"),
    )
    pytest.fail("install_os build_iso tag failed")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(2)
def test_deploy_install_os_generate_ks(host):
    """Deploy install_os.yml with generate_ks tag.

    Validates kickstart file generation. Requires source ISO for architecture detection.
    """
    tc = TC["deploy_install_os_generate_ks"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-verification: Check config has required parameters
    from library.functions import get_utils_input_path, validate_install_os_config
    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"

    config_result = validate_install_os_config(host, config_path)
    if not config_result["success"]:
        tl.failed(f"Config validation failed: {config_result['error']}")
        pytest.fail(f"Config validation failed: {config_result['error']}")

    config = config_result.get("config", {})

    # Check required parameters for generate_ks
    source_iso = config.get("source_iso_path", "")

    if not source_iso:
        tl.skipped("source_iso_path not configured in install_os_config.yml")
        pytest.skip("source_iso_path not configured")

    result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="generate_ks")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
        return

    tl.failed(
        LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
        result.get("error", "See playbook output above"),
    )
    pytest.fail("install_os generate_ks tag failed")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(3)
def test_deploy_install_os_deploy(host):
    """Deploy install_os.yml with deploy tag (iDRAC virtual media).

    Validates ISO deployment to target BMC. Requires actual hardware and proper config.
    """
    tc = TC["deploy_install_os_deploy"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-verification: Check config has required parameters
    from library.functions import get_utils_input_path, validate_install_os_config
    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"

    config_result = validate_install_os_config(host, config_path)
    if not config_result["success"]:
        tl.failed(f"Config validation failed: {config_result['error']}")
        pytest.fail(f"Config validation failed: {config_result['error']}")

    config = config_result.get("config", {})

    # Check required parameters for deploy
    custom_iso = config.get("custom_iso_path", "")
    bmc_ip = config.get("target_bmc_ip", "")
    admin_ip = config.get("target_admin_ip", "")

    if not custom_iso:
        tl.skipped("custom_iso_path not configured in install_os_config.yml")
        pytest.skip("custom_iso_path not configured")

    if not bmc_ip:
        tl.skipped("target_bmc_ip not configured in install_os_config.yml")
        pytest.skip("target_bmc_ip not configured")

    if not admin_ip:
        tl.skipped("target_admin_ip not configured in install_os_config.yml")
        pytest.skip("target_admin_ip not configured")

    result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="deploy")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
        return

    tl.failed(
        LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
        result.get("error", "See playbook output above"),
    )
    pytest.fail("install_os deploy tag failed")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(4)
def test_deploy_install_os_full(host):
    """Deploy install_os.yml with all tags (full execution).

    Validates complete end-to-end OS installation. Requires actual hardware and full config.
    """
    tc = TC["deploy_install_os_full"]
    tl = TestLogger(tc["title"], tc["id"])

    # Pre-verification: Check config has all required parameters
    from library.functions import get_utils_input_path, validate_install_os_config
    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"

    config_result = validate_install_os_config(host, config_path)
    if not config_result["success"]:
        tl.failed(f"Config validation failed: {config_result['error']}")
        pytest.fail(f"Config validation failed: {config_result['error']}")

    config = config_result.get("config", {})

    # Check all required parameters for full execution
    source_iso = config.get("source_iso_path", "")
    custom_iso = config.get("custom_iso_path", "")
    bmc_ip = config.get("target_bmc_ip", "")
    admin_ip = config.get("target_admin_ip", "")
    hostname = config.get("target_hostname", "")

    missing_params = []
    if not source_iso:
        missing_params.append("source_iso_path")
    if not custom_iso:
        missing_params.append("custom_iso_path")
    if not bmc_ip:
        missing_params.append("target_bmc_ip")
    if not admin_ip:
        missing_params.append("target_admin_ip")
    if not hostname:
        missing_params.append("target_hostname")

    if missing_params:
        tl.skipped(f"Missing required config parameters: {', '.join(missing_params)}")
        pytest.skip(f"Missing required config parameters: {', '.join(missing_params)}")

    result = run_playbook(playbook=PLAYBOOK_INSTALL_OS)

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
        return

    tl.failed(
        LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
        result.get("error", "See playbook output above"),
    )
    pytest.fail("install_os full execution failed")


# =============================================================================
# NEGATIVE TEST CASES
# =============================================================================

@pytest.mark.deploy
@pytest.mark.regression
@pytest.mark.order(10)
def test_deploy_install_os_credentials_missing_config(host):
    """Test credentials tag with missing config file - should fail gracefully."""
    tc = TC["deploy_install_os_credentials"]
    tl = TestLogger(tc["title"], tc["id"])

    # Temporarily rename config file to simulate missing config
    from library.functions import get_utils_input_path
    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"
    backup_path = f"{config_path}.backup"

    try:
        # Backup and remove config
        host.run(f"mv {config_path} {backup_path}")

        result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="credentials")

        # Should fail due to missing config
        if not result["success"]:
            err = result.get("error", "") + result.get("output", "")
            if "install_os_config" in err or "config" in err.lower():
                tl.passed("Playbook failed as expected with missing config")
            else:
                tl.failed(f"Playbook failed with unexpected error: {err}")
                pytest.fail(f"Unexpected error: {err}")
        else:
            tl.failed("Playbook should have failed with missing config")
            pytest.fail("Playbook should have failed with missing config")

    finally:
        # Restore config file
        host.run(f"mv {backup_path} {config_path} 2>/dev/null || true")


@pytest.mark.deploy
@pytest.mark.regression
@pytest.mark.order(11)
def test_deploy_install_os_build_iso_missing_source_iso(host):
    """Test build_iso tag with missing source_iso - should fail validation."""
    tc = TC["deploy_install_os_build_iso"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions import get_utils_input_path, read_remote_file
    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"

    # Read current config
    config_result = read_remote_file(host, config_path)
    if not config_result["success"]:
        tl.failed(f"Cannot read config: {config_result['error']}")
        pytest.fail(f"Cannot read config: {config_result['error']}")

    original_config = config_result["content"]

    try:
        # Set source_iso_path to empty
        modified_config = original_config.replace(
            'source_iso_path: "/root/RHEL-10.0-20250410.6-x86_64-dvd1.iso"',
            'source_iso_path: ""'
        )
        import base64
        b64 = base64.b64encode(modified_config.encode("utf-8")).decode("ascii")
        host.run(f"echo '{b64}' | base64 -d > {config_path}")

        result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="build_iso")

        # Should fail due to missing source_iso
        if not result["success"]:
            err = result.get("error", "") + result.get("output", "")
            if "source_iso_path" in err:
                tl.passed("Playbook failed as expected with missing source_iso_path")
            else:
                tl.failed(f"Playbook failed with unexpected error: {err}")
                pytest.fail(f"Unexpected error: {err}")
        else:
            tl.failed("Playbook should have failed with missing source_iso_path")
            pytest.fail("Playbook should have failed with missing source_iso_path")

    finally:
        # Restore original config
        b64 = base64.b64encode(original_config.encode("utf-8")).decode("ascii")
        host.run(f"echo '{b64}' | base64 -d > {config_path}")


@pytest.mark.deploy
@pytest.mark.regression
@pytest.mark.order(12)
def test_deploy_install_os_deploy_missing_bmc_ip(host):
    """Test deploy tag with missing BMC IP - should fail validation."""
    tc = TC["deploy_install_os_deploy"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions import get_utils_input_path, read_remote_file
    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"

    # Read current config
    config_result = read_remote_file(host, config_path)
    if not config_result["success"]:
        tl.failed(f"Cannot read config: {config_result['error']}")
        pytest.fail(f"Cannot read config: {config_result['error']}")

    original_config = config_result["content"]

    try:
        # Set target_bmc_ip to empty
        modified_config = original_config.replace(
            'target_bmc_ip: "192.168.1.100"',
            'target_bmc_ip: ""'
        )
        import base64
        b64 = base64.b64encode(modified_config.encode("utf-8")).decode("ascii")
        host.run(f"echo '{b64}' | base64 -d > {config_path}")

        result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="deploy")

        # Should fail due to missing BMC IP
        if not result["success"]:
            err = result.get("error", "") + result.get("output", "")
            if "target_bmc_ip" in err or "bmc" in err.lower():
                tl.passed("Playbook failed as expected with missing target_bmc_ip")
            else:
                tl.failed(f"Playbook failed with unexpected error: {err}")
                pytest.fail(f"Unexpected error: {err}")
        else:
            tl.failed("Playbook should have failed with missing target_bmc_ip")
            pytest.fail("Playbook should have failed with missing target_bmc_ip")

    finally:
        # Restore original config
        b64 = base64.b64encode(original_config.encode("utf-8")).decode("ascii")
        host.run(f"echo '{b64}' | base64 -d > {config_path}")
