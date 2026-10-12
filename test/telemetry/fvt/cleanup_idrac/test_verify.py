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
Telemetry Cleanup iDRAC --- Post-Cleanup Verification.

Verifies that iDRAC telemetry resources have been removed after
running ``cleanup_idrac``.

Test cases:
    TEL_FVT_CLEANUP_V006: Verify iDRAC pods removed after cleanup
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.cleanup_func import verify_idrac_cleaned


@pytest.mark.functional
@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(10)
def test_cleanup_idrac(host):
    """TEL_FVT_CLEANUP_V006: Verify iDRAC telemetry resources removed."""
    tc = TC["cleanup_idrac"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_idrac_cleaned(host)

    if result["success"]:
        tl.passed(LOG_MSGS["idrac_cleaned"], result["details"])
    else:
        tl.failed(LOG_MSGS["idrac_not_cleaned"], result["details"])

    assert result["success"], ASSERT_MSGS["idrac_not_cleaned"]
