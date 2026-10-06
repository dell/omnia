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
Telemetry Cleanup UFM --- Post-Cleanup Verification.

Verifies that UFM telemetry resources have been removed after
running ``cleanup_ufm``.

Test cases:
    TEL_FVT_CLEANUP_V009: Verify UFM resources removed after cleanup
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.ufm_msgs import (
    UFM_ASSERT_MSGS,
    UFM_LOG_MSGS,
)
from library.functions.cleanup_func import verify_ufm_cleaned


@pytest.mark.functional
@pytest.mark.source
@pytest.mark.ufm
@pytest.mark.sanity
@pytest.mark.order(10)
def test_cleanup_ufm(host):
    """TEL_FVT_CLEANUP_V009: Verify UFM telemetry resources removed."""
    tc = TC["cleanup_ufm"]
    tl = TestLogger(tc["title"], tc["id"])

    result = verify_ufm_cleaned(host)

    if result["success"]:
        tl.passed(UFM_LOG_MSGS["cleanup_complete"], result["details"])
    else:
        tl.failed(UFM_LOG_MSGS["cleanup_incomplete"], result["details"])

    assert result["success"], UFM_ASSERT_MSGS["cleanup_incomplete"]
