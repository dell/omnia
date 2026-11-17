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

"""ER-ORCH-005 IPoIB inputs the validator must accept."""

import pytest
from library.functions import TestLogger, check_ipoib_input_case
from library.vars import TEST_CASES as TC

from fvt.result import verify_precheck_input


def _verify(host, key):
    tc = TC[key]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck_input(test_log, tc, host, check_ipoib_input_case, key)


@pytest.mark.ipoib
@pytest.mark.order(10601)
def test_ipoib_input_ipv4_only_ignores_ipv6_subnet(host):
    """TC-FVT-028: ipv4-only with ipv6_subnet set raises no IB error."""
    _verify(host, "ipoib_input_ipv4_only_ignores_ipv6_subnet")


@pytest.mark.ipoib
@pytest.mark.order(10602)
def test_ipoib_input_mode_defaults_to_ipv4_only(host):
    """TC-FVT-028/TC-FVT-003: omitted ib_addr_mode is accepted as ipv4-only."""
    _verify(host, "ipoib_input_mode_defaults_to_ipv4_only")


@pytest.mark.ipoib
@pytest.mark.order(10603)
def test_ipoib_input_dual_stack_accepted(host):
    """TC-FVT-001/028: dual-stack with IPv4 and IPv6 allocations is accepted."""
    _verify(host, "ipoib_input_dual_stack_accepted")


@pytest.mark.ipoib
@pytest.mark.order(10604)
def test_ipoib_input_empty_ib_columns_skipped(host):
    """TC-FVT-006: a node with all IB columns empty is skipped without error."""
    _verify(host, "ipoib_input_empty_ib_columns_skipped")


@pytest.mark.ipoib
@pytest.mark.order(10605)
def test_ipoib_input_ipv6_only_without_ipv4(host):
    """TC-FVT-022/TC-FVT-002: ipv6-only rows need no IPv4 allocation."""
    _verify(host, "ipoib_input_ipv6_only_without_ipv4")
