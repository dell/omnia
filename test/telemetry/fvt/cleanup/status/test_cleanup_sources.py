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
Telemetry Cleanup — Source Cleanup Verification Tests.

Verifies that each telemetry source's K8s resources have been removed
after running the cleanup playbook.

Test cases:
    TEL_FVT_CLEANUP_V006: Verify cleanup_idrac removes iDRAC resources
    TEL_FVT_CLEANUP_V007: Verify cleanup_ldms removes LDMS + Vector-LDMS
    TEL_FVT_CLEANUP_V008: Verify cleanup_ome removes OME + Vector-OME
    TEL_FVT_CLEANUP_V009: Verify cleanup_ufm removes UFM resources
    TEL_FVT_CLEANUP_V010: Verify cleanup_vast removes VAST resources
    TEL_FVT_CLEANUP_V011: Verify cleanup_sfm removes SFM resources
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
from library.messages.sfm_msgs import (
    SFM_ASSERT_MSGS,
    SFM_LOG_MSGS,
from library.messages.ufm_msgs import (
    UFM_ASSERT_MSGS,
    UFM_LOG_MSGS,
from library.functions.cleanup_func import (
    verify_idrac_cleaned,
    verify_ldms_cleaned,
    verify_ome_cleaned,
    verify_ufm_cleaned,
    verify_vast_cleaned,
    verify_sfm_cleaned,


@pytest.mark.functional
@pytest.mark.order(56)
def test_cleanup_idrac(host):
    """TEL_FVT_CLEANUP_V006: Verify iDRAC telemetry resources removed after cleanup.
    
    """
    
    tc = TC["cleanup_idrac"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_idrac_cleaned(host)

    if result["success"]:
        tl.passed(LOG_MSGS["idrac_cleaned"], result["details"])
    else:
        tl.failed(LOG_MSGS["idrac_not_cleaned"], result["details"])

    assert result["success"], ASSERT_MSGS["idrac_not_cleaned"]


@pytest.mark.functional
@pytest.mark.order(57)
def test_cleanup_ldms(host):
    """TEL_FVT_CLEANUP_V007: Verify LDMS + Vector-LDMS resources removed after cleanup.
    
    """
    
    tc = TC["cleanup_ldms"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_ldms_cleaned(host)

    if result["success"]:
        tl.passed(LOG_MSGS["ldms_cleaned"], result["details"])
    else:
        tl.failed(LOG_MSGS["ldms_not_cleaned"], result["details"])

    assert result["success"], ASSERT_MSGS["ldms_not_cleaned"]


@pytest.mark.functional
@pytest.mark.order(58)
def test_cleanup_ome(host):
    """TEL_FVT_CLEANUP_V008: Verify OME + Vector-OME resources removed after cleanup.
    
    """
    
    tc = TC["cleanup_ome"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_ome_cleaned(host)

    if result["success"]:
        tl.passed(LOG_MSGS["ome_cleaned"], result["details"])
    else:
        tl.failed(LOG_MSGS["ome_not_cleaned"], result["details"])

    assert result["success"], ASSERT_MSGS["ome_not_cleaned"]


@pytest.mark.functional
@pytest.mark.order(59)
def test_cleanup_ufm(host):
    """TEL_FVT_CLEANUP_V009: Verify UFM telemetry resources removed after cleanup.
    
    """
    
    tc = TC["cleanup_ufm"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_ufm_cleaned(host)

    if result["success"]:
        tl.passed(UFM_LOG_MSGS["cleanup_complete"], result["details"])
    else:
        tl.failed(UFM_LOG_MSGS["cleanup_incomplete"], result["details"])

    assert result["success"], UFM_ASSERT_MSGS["cleanup_incomplete"]


@pytest.mark.functional
@pytest.mark.order(60)
def test_cleanup_vast(host):
    """TEL_FVT_CLEANUP_V010: Verify VAST telemetry resources removed after cleanup.
    
    """
    
    tc = TC["cleanup_vast"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_vast_cleaned(host)

    if result["success"]:
        tl.passed(LOG_MSGS["vast_cleaned"], result["details"])
    else:
        tl.failed(LOG_MSGS["vast_not_cleaned"], result["details"])

    assert result["success"], ASSERT_MSGS["vast_not_cleaned"]


@pytest.mark.functional
@pytest.mark.order(61)
def test_cleanup_sfm(host):
    """TEL_FVT_CLEANUP_V011: Verify SFM telemetry resources removed after cleanup.
    
    """
    
    tc = TC["cleanup_sfm"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_sfm_cleaned(host)

    if result["success"]:
        tl.passed(SFM_LOG_MSGS["cleanup_complete"], result["details"])
    else:
        tl.failed(SFM_LOG_MSGS["cleanup_incomplete"], result["details"])

    assert result["success"], SFM_ASSERT_MSGS["cleanup_incomplete"]
