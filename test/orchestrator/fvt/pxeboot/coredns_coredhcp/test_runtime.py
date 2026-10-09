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
    TestLogger,
    check_coredhcp_config_file,
    check_coredhcp_multisubnet_running_image,
    check_coredns_container_state,
    check_coredns_corefile_config,
    check_coredns_dns_forwarders,
    check_coredns_forward_resolution,
    check_coredns_idempotency,
    check_coredns_reverse_resolution,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot

@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.non_disruptive
@pytest.mark.order(40701)
def test_coredns_container_state(host):
    """TC-01: coresmd containers match the dns_enabled dataset (enabled+disabled)."""
    tc = TC["coredns_container_state"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_coredns_container_state)


@pytest.mark.buildstream
@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.non_disruptive
@pytest.mark.order(40702)
def test_coredns_forward_resolution(host):
    """TC-02: dig FQDN from OIM for every mapped node; compare to ADMIN_IP."""
    tc = TC["coredns_forward_resolution"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_coredns_forward_resolution)


@pytest.mark.buildstream
@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.non_disruptive
@pytest.mark.order(40703)
def test_coredns_reverse_resolution(host):
    """TC-03: dig -x from OIM for every mapped ADMIN_IP; compare to FQDN."""
    tc = TC["coredns_reverse_resolution"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_coredns_reverse_resolution)


@pytest.mark.buildstream
@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.non_disruptive
@pytest.mark.order(40704)
def test_coredns_dns_forwarders(host):
    """TC-04: verify DNS forwarders are configured and can resolve external domains."""
    tc = TC["coredns_dns_forwarders"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_coredns_dns_forwarders)


@pytest.mark.buildstream
@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.non_disruptive
@pytest.mark.order(40705)
def test_coredns_corefile_config(host):
    """TC-05: verify Corefile configuration is correctly rendered."""
    tc = TC["coredns_corefile_config"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_coredns_corefile_config)


@pytest.mark.buildstream
@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.non_disruptive
@pytest.mark.order(40706)
def test_coredhcp_config_file(host):
    """TC-06: verify coredhcp.yaml configuration file is correctly rendered."""
    tc = TC["coredhcp_config_file"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_coredhcp_config_file)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.non_disruptive
@pytest.mark.order(40707)
def test_coredhcp_multisubnet_running_image(host):
    """TC-07: multi-subnet dataset -> coresmd containers use expected image."""
    tc = TC["coredhcp_multisubnet_running_image"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_coredhcp_multisubnet_running_image)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.non_disruptive
@pytest.mark.order(40708)
def test_coredns_idempotency(host):
    """TC-08: coresmd state stability (no-drift) across a settle window."""
    tc = TC["coredns_idempotency"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_coredns_idempotency)
