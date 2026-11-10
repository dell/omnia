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

"""ER-ORCH-005 IPoIB inputs the validator must reject."""

import pytest
from library.functions import TestLogger, check_ipoib_input_case
from library.vars import TEST_CASES as TC

from fvt.result import verify_precheck_input


def _verify(host, key):
    tc = TC[key]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck_input(test_log, tc, host, check_ipoib_input_case, key)


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10606)
def test_neg_ipoib_ipv6_subnet_malformed(host):
    """TC-FVT-004/028: malformed ipv6_subnet is rejected."""
    _verify(host, "neg_ipoib_ipv6_subnet_malformed")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10607)
def test_neg_ipoib_ipv6_prefix_length_invalid(host):
    """TC-FVT-004/028: out-of-range ipv6_netmask_bits is rejected."""
    _verify(host, "neg_ipoib_ipv6_prefix_length_invalid")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10608)
def test_neg_ipoib_dual_stack_missing_ipv6_subnet(host):
    """TC-FVT-001: dual-stack without an IPv6 prefix is rejected."""
    _verify(host, "neg_ipoib_dual_stack_missing_ipv6_subnet")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10609)
def test_neg_ipoib_addr_mode_unsupported(host):
    """FR-1: an unsupported ib_addr_mode is rejected."""
    _verify(host, "neg_ipoib_addr_mode_unsupported")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10610)
def test_neg_ipoib_gateway_input(host):
    """TC-FVT-010: an IPoIB gateway input is rejected."""
    _verify(host, "neg_ipoib_gateway_input")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10611)
def test_neg_ipoib_static_route_input(host):
    """TC-FVT-010: a static IPoIB route input is rejected."""
    _verify(host, "neg_ipoib_static_route_input")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10612)
def test_neg_ipoib_default_route_input(host):
    """TC-FVT-010: an IB default route input is rejected."""
    _verify(host, "neg_ipoib_default_route_input")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10613)
def test_neg_ipoib_pxe_ipv6_unparseable(host):
    """TC-FVT-029: an unparseable IB_IPV6 is rejected."""
    _verify(host, "neg_ipoib_pxe_ipv6_unparseable")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10614)
def test_neg_ipoib_pxe_ipv4_unparseable(host):
    """TC-FVT-029: an unparseable IB_IPV4 is rejected."""
    _verify(host, "neg_ipoib_pxe_ipv4_unparseable")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10615)
def test_neg_ipoib_pxe_ipv4_in_ipv6_column(host):
    """TC-FVT-029: an IPv4 address in IB_IPV6 is rejected."""
    _verify(host, "neg_ipoib_pxe_ipv4_in_ipv6_column")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10616)
def test_neg_ipoib_pxe_ipv6_duplicate(host):
    """TC-FVT-006: a duplicate IB_IPV6 is rejected."""
    _verify(host, "neg_ipoib_pxe_ipv6_duplicate")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10617)
def test_neg_ipoib_pxe_ipv6_duplicate_expanded(host):
    """TC-FVT-007/029: compressed and expanded duplicates are rejected."""
    _verify(host, "neg_ipoib_pxe_ipv6_duplicate_expanded")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10618)
def test_neg_ipoib_pxe_ipv6_without_nic_name(host):
    """TC-FVT-006: IB_IPV6 without IB_NIC_NAME is rejected."""
    _verify(host, "neg_ipoib_pxe_ipv6_without_nic_name")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10619)
def test_neg_ipoib_pxe_ipv6_outside_prefix(host):
    """TC-FVT-006: IB_IPV6 outside the approved prefix is rejected."""
    _verify(host, "neg_ipoib_pxe_ipv6_outside_prefix")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10620)
def test_neg_ipoib_pxe_dual_stack_missing_ipv6(host):
    """TC-FVT-022: dual-stack row without IB_IPV6 is rejected."""
    _verify(host, "neg_ipoib_pxe_dual_stack_missing_ipv6")


@pytest.mark.negative
@pytest.mark.ipoib
@pytest.mark.order(10621)
def test_neg_ipoib_pxe_dual_stack_missing_ipv4(host):
    """TC-FVT-022: dual-stack row without IB_IPV4 is rejected."""
    _verify(host, "neg_ipoib_pxe_dual_stack_missing_ipv4")
