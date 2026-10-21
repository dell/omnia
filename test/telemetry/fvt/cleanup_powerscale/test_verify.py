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
Telemetry Cleanup PowerScale --- Post-Cleanup Verification.

Verifies that PowerScale telemetry resources have been removed after
running ``cleanup_powerscale``.

Test cases:
    TEL_FVT_CLEANUP_POWERSCALE_V001: Verify PowerScale resources removed
"""

import pytest

from omnia_auto import TestLogger

from library.vars.test_case_vars import TEST_CASES as TC
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import verify_pods_by_prefix


@pytest.mark.functional
@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(10)
def test_cleanup_powerscale(host):
    """TEL_FVT_CLEANUP_POWERSCALE_V001: Verify PowerScale resources removed."""
    tc = TC["cleanup_powerscale"]
    tl = TestLogger(tc["title"], tc["id"])

    # PowerScale pods use prefixes like "powerscale", "csm-metrics-powerscale"
    prefixes = ["powerscale", "csm-metrics-powerscale"]
    all_cleaned = True
    details = []
    for prefix in prefixes:
        result = verify_pods_by_prefix(host, prefix, min_count=0)
        count = result.get("count", 0)
        if count > 0:
            all_cleaned = False
            details.append(f"{prefix}: {count} pod(s) still running")
        else:
            details.append(f"{prefix}: cleaned")

    summary = "\n".join(details)
    if all_cleaned:
        tl.passed("PowerScale resources removed", summary)
    else:
        tl.failed("PowerScale resources not fully removed", summary)

    assert all_cleaned, f"PowerScale cleanup incomplete: {summary}"
