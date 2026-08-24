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
Set PXE Boot Scenario — Playbook Deployment Tests.

Tests for deploying the set_pxe_boot.yml playbook with various tags.
"""

import pytest

from library.functions import (
    TestLogger,
    run_playbook,
    load_test_config,
    get_utils_input_path,
    check_file_exists,
)
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_SET_PXE_BOOT,
    PLAYBOOK_WORKDIR,
    SET_PXE_BOOT_INVENTORY_FILE,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.pxe
@pytest.mark.order(0)
def test_deploy_pxe_credentials(host):
    """Deploy set_pxe_boot.yml with credentials tag."""
    tc = TC["deploy_pxe_credentials"]
    tl = TestLogger(tc["title"], tc["id"])

    result = run_playbook(playbook=PLAYBOOK_SET_PXE_BOOT, tag="credentials")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_SET_PXE_BOOT,
        tag="credentials",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" + PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.pxe
@pytest.mark.order(1)
def test_deploy_pxe_boot(host):
    """Deploy set_pxe_boot.yml with pxe_boot tag.

    Note: This test requires a valid inventory file with BMC hosts.
    It will be skipped if no inventory file is found.
    """
    tc = TC["deploy_pxe_boot"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if inventory file exists
    input_path = get_utils_input_path(host)
    inventory_path = f"{input_path}/{SET_PXE_BOOT_INVENTORY_FILE}"

    inv_result = check_file_exists(host, inventory_path)
    if not inv_result["success"]:
        tl.skipped("Inventory file not found, skipping PXE boot test")
        pytest.skip(f"Inventory file not found: {inventory_path}")

    result = run_playbook(
        playbook=PLAYBOOK_SET_PXE_BOOT,
        tag="pxe_boot",
        inventory=inventory_path,
    )

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_SET_PXE_BOOT,
        tag="pxe_boot",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" + PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.pxe
@pytest.mark.order(2)
def test_deploy_pxe_full(host):
    """Deploy set_pxe_boot.yml with all tags (full execution).

    Note: This test requires a valid inventory file with BMC hosts.
    It will be skipped if no inventory file is found.
    """
    tc = TC["deploy_pxe_full"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check if inventory file exists
    input_path = get_utils_input_path(host)
    inventory_path = f"{input_path}/{SET_PXE_BOOT_INVENTORY_FILE}"

    inv_result = check_file_exists(host, inventory_path)
    if not inv_result["success"]:
        tl.skipped("Inventory file not found, skipping full PXE boot test")
        pytest.skip(f"Inventory file not found: {inventory_path}")

    # Run without tag to execute all plays
    result = run_playbook(
        playbook=PLAYBOOK_SET_PXE_BOOT,
        tag=None,
    )

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_SET_PXE_BOOT,
        tag="(all)",
        rc=result["rc"],
        duration=result["duration"],
        input_path=get_utils_input_path(host),
        workdir=config.get("clone_path", "/root/omnia") + "/" + PLAYBOOK_WORKDIR.replace("playbooks/", ""),
    )
