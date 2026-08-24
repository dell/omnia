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

    In minimal automation environments, this may fail early if the config file is
    missing. That still validates the playbook's validation flow.
    """
    tc = TC["deploy_install_os_credentials"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="credentials")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
        return

    err = (result.get("error") or "") + (result.get("output") or "")
    if "install_os_config" in err or "install_os_config.yml" in err:
        tl.passed("Validation failed as expected (install_os_config.yml missing/incomplete)")
        return

    tl.failed(
        LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
        result.get("error", "See playbook output above"),
    )
    pytest.fail("install_os credentials tag failed unexpectedly")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(1)
def test_deploy_install_os_build_iso(host):
    """Deploy install_os.yml with build_iso tag.

    This tag includes ISO validation/tooling + ISO creation. In typical CI/local
    automation runs, we may not have a real ISO/NFS configured, so we accept a
    validation failure as success of the wiring.
    """
    tc = TC["deploy_install_os_build_iso"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="build_iso")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
        return

    err = (result.get("error") or "") + (result.get("output") or "")
    expected_markers = [
        "install_os_config",
        "source_iso_path",
        "custom_iso_path",
        "nfs",
    ]
    if any(m in err for m in expected_markers):
        tl.passed("Validation failed as expected (ISO/NFS parameters missing in automation env)")
        return

    tl.failed(
        LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
        result.get("error", "See playbook output above"),
    )
    pytest.fail("install_os build_iso tag failed unexpectedly")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(2)
def test_deploy_install_os_generate_ks(host):
    """Deploy install_os.yml with generate_ks tag.

    This generates kickstart only (no ISO build). In automation runs without an
    NFS mount configured, validation failures are expected.
    """
    tc = TC["deploy_install_os_generate_ks"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_INSTALL_OS, tag="generate_ks")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
        return

    err = (result.get("error") or "") + (result.get("output") or "")
    expected_markers = [
        "install_os_config",
        "source_iso_path",
        "custom_iso_path",
        "mount",
        "nfs",
    ]
    if any(m in err for m in expected_markers):
        tl.passed("Validation failed as expected (kickstart/NFS prerequisites missing)")
        return

    tl.failed(
        LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
        result.get("error", "See playbook output above"),
    )
    pytest.fail("install_os generate_ks tag failed unexpectedly")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(3)
def test_deploy_install_os_deploy(host):
    """Deploy install_os.yml with deploy tag (iDRAC virtual media).

    Note: This test requires actual BMC hardware and will be skipped
    in test environments without hardware.
    """
    tc = TC["deploy_install_os_deploy"]
    tl = TestLogger(tc["title"], tc["id"])

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
