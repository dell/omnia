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

"""OIM-side CoreDNS/CoreDHCP runtime contracts (non-disruptive).

Closes the 2.2 -> 2.3 coverage gap identified in ORCH-FUNC-TEST-008 for
the OIM side: container state under the enabled/disabled/multi-subnet
datasets, forward and reverse DNS resolution proven against the exact
PXE mapping, and repeated-deployment stability.
"""

import pytest
from library.functions import (
    check_coredhcp_multisubnet_running_image,
    check_coredns_container_state,
    check_coredns_forward_resolution,
    check_coredns_idempotency,
    check_coredns_reverse_resolution,
)

from fvt.result import verify_pxeboot

pytestmark = [pytest.mark.non_disruptive]


@pytest.mark.sanity
@pytest.mark.order(350)
def test_coredns_container_state(host):
    """TC-01: coresmd containers match the dns_enabled dataset (enabled+disabled)."""
    verify_pxeboot(host, "coredns_container_state", check_coredns_container_state)


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.order(351)
def test_coredns_forward_resolution(host):
    """TC-02: dig FQDN from OIM for every mapped node; compare to ADMIN_IP."""
    verify_pxeboot(
        host, "coredns_forward_resolution", check_coredns_forward_resolution
    )


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.order(352)
def test_coredns_reverse_resolution(host):
    """TC-03: dig -x from OIM for every mapped ADMIN_IP; compare to FQDN."""
    verify_pxeboot(
        host, "coredns_reverse_resolution", check_coredns_reverse_resolution
    )


@pytest.mark.sanity
@pytest.mark.order(353)
def test_coredhcp_multisubnet_running_image(host):
    """TC-04: multi-subnet dataset -> coresmd containers use expected image."""
    verify_pxeboot(
        host,
        "coredhcp_multisubnet_running_image",
        check_coredhcp_multisubnet_running_image,
    )


@pytest.mark.sanity
@pytest.mark.order(354)
def test_coredns_idempotency(host):
    """TC-07: coresmd state stability (no-drift) across a settle window."""
    verify_pxeboot(host, "coredns_idempotency", check_coredns_idempotency)
