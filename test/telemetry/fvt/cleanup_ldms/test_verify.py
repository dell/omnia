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
Telemetry Cleanup LDMS --- Post-Cleanup Verification.

Verifies that LDMS aggregator, store, and Vector-LDMS bridge resources
have been removed after running ``cleanup_ldms``.

Test cases:
    TEL_FVT_CLEANUP_V007: Verify LDMS pods removed after cleanup
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.cleanup_func import verify_ldms_cleaned


@pytest.mark.functional
@pytest.mark.source
@pytest.mark.ldms
@pytest.mark.sanity
@pytest.mark.order(10)
def test_cleanup_ldms(host):
    """TEL_FVT_CLEANUP_V007: Verify LDMS + Vector-LDMS resources removed."""
    tc = TC["cleanup_ldms"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_ldms_cleaned(host)

    if result["success"]:
        tl.passed(LOG_MSGS["ldms_cleaned"], result["details"])
    else:
        tl.failed(LOG_MSGS["ldms_not_cleaned"], result["details"])

    assert result["success"], ASSERT_MSGS["ldms_not_cleaned"]
