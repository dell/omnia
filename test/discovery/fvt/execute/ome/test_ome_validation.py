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
Discovery — OME Integration Validation Tests.

These tests verify the discovery output against live OME data.
They require OME connectivity and valid credentials configured in
test_config.yml under the 'ome' section.

Test Cases:
- DISCOVERY_FVT_EXECUTE_V010: Verify OME static groups match PXE mapping
- DISCOVERY_FVT_EXECUTE_V011: Verify OME devices without static group
- DISCOVERY_FVT_EXECUTE_V012: Verify ADMIN_MAC matches OME NIC
- DISCOVERY_FVT_EXECUTE_V013: Verify IB_NIC_NAME matches OME IB NIC

Note: These tests are skipped if OME is not configured in test_config.yml.
"""

import pytest

from library.functions import (
    TestLogger,
    check_ome_static_groups_match,
    check_ome_unassigned_devices,
    check_admin_mac_validation,
    check_ib_nic_name_validation,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
)
from library.vars.test_case_vars import TEST_CASES as TC


@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(10)
def test_ome_static_groups_match(host):
    """DISCOVERY_FVT_EXECUTE_V010: Verify OME static groups match PXE mapping."""
    tc = TC["ome_static_groups_match"]
    tl = TestLogger(TEST_NAMES["ome_static_groups_match"], tc["id"])
    result = check_ome_static_groups_match(host)

    if result.get("skipped"):
        tl.skipped(LOG["ome_skipped"], result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["ome_groups_match_ok"].format(
                count=len(result.get("matched_groups", []))
            ),
            result["details"]
        )
    else:
        tl.failed(
            LOG["ome_groups_mismatch"].format(
                groups=", ".join(result.get("unmatched_pxe", []))
            ),
            result["details"]
        )

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(11)
def test_ome_unassigned_devices(host):
    """DISCOVERY_FVT_EXECUTE_V011: Verify OME devices without static group."""
    tc = TC["ome_unassigned_devices"]
    tl = TestLogger(TEST_NAMES["ome_unassigned_devices"], tc["id"])
    result = check_ome_unassigned_devices(host)

    if result.get("skipped"):
        tl.skipped(LOG["ome_skipped"], result["details"])
        pytest.skip(result["details"])

    # This test always passes - it's informational
    # It reports how many devices are not assigned to static groups
    tl.passed(
        LOG["ome_unassigned_ok"].format(count=result["unassigned_count"]),
        result["details"]
    )

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(12)
def test_admin_mac_validation(host):
    """DISCOVERY_FVT_EXECUTE_V012: Verify ADMIN_MAC matches OME NIC."""
    tc = TC["admin_mac_validation"]
    tl = TestLogger(TEST_NAMES["admin_mac_validation"], tc["id"])
    result = check_admin_mac_validation(host)

    if result.get("skipped"):
        tl.skipped(LOG["ome_skipped"], result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["admin_mac_ok"].format(count=result["valid_count"]),
            result["details"]
        )
    else:
        # Show MAC mismatches concisely
        mac_list = result.get("mac_mismatches", [])
        detail_str = "; ".join(mac_list[:5])  # Show first 5
        if len(mac_list) > 5:
            detail_str += f" (+{len(mac_list) - 5} more)"
        tl.failed(
            LOG["admin_mac_failed"].format(
                count=len(result.get("invalid_rows", []))
            ),
            detail_str
        )

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.ome
@pytest.mark.order(13)
def test_ib_nic_name_validation(host):
    """DISCOVERY_FVT_EXECUTE_V013: Verify IB_NIC_NAME matches OME IB NIC."""
    tc = TC["ib_nic_name_validation"]
    tl = TestLogger(TEST_NAMES["ib_nic_name_validation"], tc["id"])
    result = check_ib_nic_name_validation(host)

    if result.get("skipped"):
        tl.skipped(LOG["ome_skipped"], result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(
            LOG["ib_nic_ok"].format(count=result["valid_count"]),
            result["details"]
        )
    else:
        tl.failed(
            LOG["ib_nic_failed"].format(
                count=len(result.get("invalid_rows", []))
            ),
            result["details"]
        )

    assert result["success"], result["error"]
