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

"""Compute-node CoreDNS behavior contracts (non-disruptive).

Closes the ticket's "query from every applicable node" requirement:
Omnia 2.3 previously had zero DNS assertions on compute nodes even
though ``provision_common/tasks/configure_dns.yml`` deploys CoreDNS
as the primary nameserver on every provisioned node.
"""

import pytest
from library.functions import (
    check_dns_compute_forward_getent,
    check_dns_compute_resolv_conf,
)

from fvt.result import verify_pxeboot

pytestmark = [pytest.mark.slurm, pytest.mark.non_disruptive]


@pytest.mark.sanity
@pytest.mark.order(355)
def test_dns_compute_resolv_conf(host):
    """TC-05: /etc/resolv.conf on every compute has CoreDNS as primary."""
    verify_pxeboot(host, "dns_compute_resolv_conf", check_dns_compute_resolv_conf)


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.order(356)
def test_dns_compute_forward_getent(host):
    """TC-06: getent hosts on every compute resolves every mapped peer."""
    verify_pxeboot(
        host, "dns_compute_forward_getent", check_dns_compute_forward_getent
    )
