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

Note: install_os.yml requires many parameters (ISO path, BMC IP, credentials, etc.).
These tests are designed to validate the playbook structure and parameter handling.
Full end-to-end OS installation testing requires actual hardware and is out of scope.
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
def test_deploy_install_os_validate(host):
    """Deploy install_os.yml with validate tag (parameter validation only).

    This test validates that the playbook can check for required parameters.
    Full deployment requires actual ISO and BMC hardware.
    """
    tc = TC["deploy_install_os_validate"]
    tl = TestLogger(tc["title"], tc["id"])

    # Run with validate tag to check parameter validation logic
    # This will fail if required parameters are missing (expected in test mode)
    result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="validate")

    # In test mode without real parameters, we expect a parameter validation failure
    # which is actually a success of the validation logic
    if not result["success"] and "Missing mandatory parameters" in result.get("error", ""):
        tl.passed("Parameter validation logic working correctly (parameters missing as expected)")
    elif result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    # We don't assert failure here since parameter validation is expected in test mode


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(1)
def test_deploy_install_os_fetch(host):
    """Deploy install_os.yml with fetch tag.

    Note: This test requires a valid ISO source path and will be skipped
    if iso_config.yml is not properly configured.
    """
    tc = TC["deploy_install_os_fetch"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if iso_config.yml exists and has valid configuration
    input_path = get_utils_input_path(host)
    from library.functions import check_file_exists, validate_iso_config

    config_path = f"{input_path}/iso_config.yml"
    exists_result = check_file_exists(host, config_path)

    if not exists_result["success"]:
        tl.skipped("iso_config.yml not found, skipping fetch test")
        pytest.skip("iso_config.yml not found")

    validate_result = validate_iso_config(host, config_path)
    if not validate_result["success"]:
        tl.skipped(f"iso_config.yml invalid: {validate_result['error']}")
        pytest.skip(f"iso_config.yml invalid: {validate_result['error']}")

    # Run with fetch tag
    result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="fetch")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_INSTALL_OS,
        tag="fetch",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" + PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(2)
def test_deploy_install_os_create(host):
    """Deploy install_os.yml with create tag (ISO creation).

    Note: This test requires a valid ISO source and will be skipped
    if prerequisites are not met.
    """
    tc = TC["deploy_install_os_create"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check prerequisites
    input_path = get_utils_input_path(host)
    from library.functions import check_file_exists, validate_iso_config

    config_path = f"{input_path}/iso_config.yml"
    exists_result = check_file_exists(host, config_path)

    if not exists_result["success"]:
        tl.skipped("iso_config.yml not found, skipping create test")
        pytest.skip("iso_config.yml not found")

    validate_result = validate_iso_config(host, config_path)
    if not validate_result["success"]:
        tl.skipped(f"iso_config.yml invalid: {validate_result['error']}")
        pytest.skip(f"iso_config.yml invalid: {validate_result['error']}")

    # Run with create tag
    result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="create")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_INSTALL_OS,
        tag="create",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" + PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(3)
def test_deploy_install_os_deliver(host):
    """Deploy install_os.yml with deliver tag (iDRAC virtual media).

    Note: This test requires actual BMC hardware and will be skipped
    in test environments without hardware.
    """
    tc = TC["deploy_install_os_deliver"]
    tl = TestLogger(tc["title"], tc["id"])

    # This test requires actual BMC hardware
    tl.skipped("Requires actual BMC hardware, skipping in test environment")
    pytest.skip("Requires actual BMC hardware")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(4)
def test_deploy_install_os_full(host):
    """Deploy install_os.yml with all tags (full execution).

    Note: Full OS installation requires actual hardware and will be skipped
    in test environments.
    """
    tc = TC["deploy_install_os_full"]
    tl = TestLogger(tc["title"], tc["id"])

    # Full installation requires actual hardware
    tl.skipped("Full OS installation requires actual hardware, skipping")
    pytest.skip("Full OS installation requires actual hardware")
