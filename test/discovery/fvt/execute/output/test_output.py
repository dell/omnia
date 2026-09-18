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
Discovery — Output Verification Tests.

TC_DS_001: Verify output directory exists
TC_DS_002: Verify PXE mapping CSV created
TC_DS_003: Verify PXE mapping CSV has required columns
TC_DS_004: Verify PXE mapping CSV has data rows
TC_DS_005: Verify PXE mapping symlink points to latest
TC_DS_006: Verify discovery report CSV created
"""

import pytest

from library.functions import (
    TestLogger,
    check_output_dir_exists,
    check_pxe_mapping_created,
    check_pxe_mapping_columns,
    check_pxe_mapping_has_rows,
    check_pxe_mapping_symlink,
    check_discovery_report_created,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.test_case_vars import TEST_CASES as TC


@pytest.mark.sanity
@pytest.mark.order(1)
def test_output_dir_exists(host):
    """TC_DS_001: Verify output directory exists."""
    tc = TC["output_dir_exists"]
    tl = TestLogger(TEST_NAMES["output_dir_exists"], tc["id"])
    result = check_output_dir_exists(host)

    if result["success"]:
        tl.passed(LOG["output_dir_ok"], result["details"])
    else:
        tl.failed(LOG["output_dir_missing"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(2)
def test_pxe_mapping_created(host):
    """TC_DS_002: Verify PXE mapping CSV created."""
    tc = TC["pxe_mapping_created"]
    tl = TestLogger(TEST_NAMES["pxe_mapping_created"], tc["id"])
    result = check_pxe_mapping_created(host)

    if result["success"]:
        tl.passed(LOG["pxe_mapping_ok"], result["details"])
    else:
        tl.failed(LOG["pxe_mapping_missing"], result["details"])

    assert result["success"], ASSERT["pxe_mapping_missing"]


@pytest.mark.functional
@pytest.mark.order(3)
def test_pxe_mapping_columns(host):
    """TC_DS_003: Verify PXE mapping CSV has required columns."""
    tc = TC["pxe_mapping_columns"]
    tl = TestLogger(TEST_NAMES["pxe_mapping_columns"], tc["id"])
    result = check_pxe_mapping_columns(host)

    if result["success"]:
        tl.passed(LOG["pxe_mapping_columns_ok"].format(
            columns="FUNCTIONAL_GROUP_NAME, SERVICE_TAG, HOSTNAME, "
                    "ADMIN_MAC, ADMIN_IP, BMC_IP"
        ), result["details"])
    else:
        tl.failed(LOG["pxe_mapping_columns_missing"].format(
            missing=result["error"]
        ), result["details"])

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(4)
def test_pxe_mapping_has_rows(host):
    """TC_DS_004: Verify PXE mapping CSV has data rows."""
    tc = TC["pxe_mapping_has_rows"]
    tl = TestLogger(TEST_NAMES["pxe_mapping_has_rows"], tc["id"])
    result = check_pxe_mapping_has_rows(host)

    if result["success"]:
        tl.passed(LOG["pxe_mapping_rows_ok"].format(
            count=result["details"]
        ))
    else:
        tl.failed(LOG["pxe_mapping_rows_empty"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(5)
def test_pxe_mapping_symlink(host):
    """TC_DS_005: Verify PXE mapping symlink points to latest."""
    tc = TC["pxe_mapping_symlink"]
    tl = TestLogger(TEST_NAMES["pxe_mapping_symlink"], tc["id"])
    result = check_pxe_mapping_symlink(host)

    if result["success"]:
        tl.passed(LOG["pxe_symlink_ok"], result["details"])
    else:
        tl.failed(LOG["pxe_symlink_missing"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(6)
def test_discovery_report_created(host):
    """TC_DS_006: Verify discovery report CSV created."""
    tc = TC["discovery_report_created"]
    tl = TestLogger(TEST_NAMES["discovery_report_created"], tc["id"])
    result = check_discovery_report_created(host)

    if result["success"]:
        tl.passed(LOG["discovery_report_ok"], result["details"])
    else:
        tl.failed(LOG["discovery_report_missing"], result["details"])

    assert result["success"], result["error"]
