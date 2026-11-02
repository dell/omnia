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

"""TC-FVT-016: dual-stack IPoIB failure modes on a live node.

Injects a runtime-only fault on one compute node, classifies the live
interface with the product verifier, and restores the node to HEALTHY.
"""

import pytest
from library.functions import (
    TestLogger,
    check_ipoib_failure_dual_stack,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.ipoib
@pytest.mark.fault_injection
@pytest.mark.order(42601)
def test_ipoib_failure_dual_stack(host):
    """TC-FVT-016 S1: dual-stack IPv6 failure is DEGRADED_IPV6; IPv4 is preserved."""
    tc = TC["ipoib_failure_dual_stack"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_ipoib_failure_dual_stack)
