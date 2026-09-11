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
Discovery Cleanup — Verification Tests.

DISCOVERY_FVT_CLEANUP_V001: Verify output directory is empty after cleanup
DISCOVERY_FVT_CLEANUP_V002: Verify credentials file is removed after cleanup
DISCOVERY_FVT_CLEANUP_V003: Verify credentials file is preserved when cleanup_credentials=false
DISCOVERY_FVT_CLEANUP_V004: Verify PXE mapping files are removed after cleanup
DISCOVERY_FVT_CLEANUP_V005: Verify discovery report files are removed after cleanup
DISCOVERY_FVT_CLEANUP_V006: Verify discovery status files are removed after cleanup
DISCOVERY_FVT_CLEANUP_V007: Verify log files are removed after cleanup
DISCOVERY_FVT_CLEANUP_V008: Verify log files are preserved when cleanup_logs=false
"""

import pytest

from library.functions import (
    TestLogger,
    check_output_dir_removed,
    check_credentials_removed,
    check_credentials_preserved,
    check_pxe_mapping_files_removed,
    check_discovery_report_files_removed,
    check_status_files_removed,
    check_log_files_removed,
    check_log_files_preserved,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.test_case_vars import TEST_CASES as TC


@pytest.mark.sanity
@pytest.mark.order(1)
def test_output_dir_removed(host):
    """DISCOVERY_FVT_CLEANUP_V001: Verify output directory is empty after cleanup."""
    tc = TC["output_dir_removed"]
    tl = TestLogger(TEST_NAMES["output_dir_removed"], tc["id"])
    result = check_output_dir_removed(host)

    if result["success"]:
        tl.passed(LOG["output_dir_removed_ok"], result["details"])
    else:
        tl.failed(LOG["output_dir_not_empty"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(2)
def test_credentials_removed(host):
    """DISCOVERY_FVT_CLEANUP_V002: Verify credentials file is removed after cleanup."""
    tc = TC["credentials_removed"]
    tl = TestLogger(TEST_NAMES["credentials_removed"], tc["id"])
    result = check_credentials_removed(host)

    if result["success"]:
        tl.passed(LOG["credentials_removed_ok"], result["details"])
    else:
        tl.failed(LOG["credentials_not_removed"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(3)
def test_credentials_preserved(host):
    """DISCOVERY_FVT_CLEANUP_V003: Verify credentials file is preserved when cleanup_credentials=false."""
    tc = TC["credentials_preserved"]
    tl = TestLogger(TEST_NAMES["credentials_preserved"], tc["id"])
    result = check_credentials_preserved(host)

    if result["success"]:
        tl.passed(LOG["credentials_preserved_ok"], result["details"])
    else:
        tl.failed(LOG["credentials_not_preserved"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(4)
def test_pxe_mapping_files_removed(host):
    """DISCOVERY_FVT_CLEANUP_V004: Verify PXE mapping files are removed after cleanup."""
    tc = TC["pxe_mapping_files_removed"]
    tl = TestLogger(TEST_NAMES["pxe_mapping_files_removed"], tc["id"])
    result = check_pxe_mapping_files_removed(host)

    if result["success"]:
        tl.passed(LOG["pxe_mapping_files_removed_ok"], result["details"])
    else:
        tl.failed(LOG["pxe_mapping_files_not_removed"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(5)
def test_discovery_report_files_removed(host):
    """DISCOVERY_FVT_CLEANUP_V005: Verify discovery report files are removed after cleanup."""
    tc = TC["discovery_report_files_removed"]
    tl = TestLogger(TEST_NAMES["discovery_report_files_removed"], tc["id"])
    result = check_discovery_report_files_removed(host)

    if result["success"]:
        tl.passed(LOG["discovery_report_files_removed_ok"], result["details"])
    else:
        tl.failed(LOG["discovery_report_files_not_removed"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(6)
def test_status_files_removed(host):
    """DISCOVERY_FVT_CLEANUP_V006: Verify discovery status files are removed after cleanup."""
    tc = TC["status_files_removed"]
    tl = TestLogger(TEST_NAMES["status_files_removed"], tc["id"])
    result = check_status_files_removed(host)

    if result["success"]:
        tl.passed(LOG["status_files_removed_ok"], result["details"])
    else:
        tl.failed(LOG["status_files_not_removed"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(7)
def test_log_files_removed(host):
    """DISCOVERY_FVT_CLEANUP_V007: Verify log files are removed after cleanup."""
    tc = TC["log_files_removed"]
    tl = TestLogger(TEST_NAMES["log_files_removed"], tc["id"])
    result = check_log_files_removed(host)

    if result["success"]:
        tl.passed(LOG["log_files_removed_ok"], result["details"])
    else:
        tl.failed(LOG["log_files_not_removed"], result["details"])

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(8)
def test_log_files_preserved(host):
    """DISCOVERY_FVT_CLEANUP_V008: Verify log files are preserved when cleanup_logs=false."""
    tc = TC["log_files_preserved"]
    tl = TestLogger(TEST_NAMES["log_files_preserved"], tc["id"])
    result = check_log_files_preserved(host)

    if result["success"]:
        tl.passed(LOG["log_files_preserved_ok"], result["details"])
    else:
        tl.failed(LOG["log_files_not_preserved"], result["details"])

    assert result["success"], result["error"]
