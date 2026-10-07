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

"""Destructive CoreDNS/CoreDHCP contracts (opt-in via OMNIA_COREDNS_DESTRUCTIVE=1).

Closes the ticket's node-addition and SMD-unavailable dataset requirements.
Both tests reach into service state on the OIM; the suite-local conftest
skips them unless OMNIA_COREDNS_DESTRUCTIVE=1 is set.
"""

import pytest
from library.functions import (
    check_dns_node_addition_pipeline,
    check_dns_smd_unreachable_cached_resolution,
)

from fvt.result import verify_pxeboot

pytestmark = [pytest.mark.destructive]


@pytest.mark.functional
@pytest.mark.order(357)
def test_dns_node_addition_pipeline(host):
    """TC-08: prove SMD-to-CoreDNS pipeline resolves every mapped node."""
    verify_pxeboot(
        host, "dns_node_addition_pipeline", check_dns_node_addition_pipeline
    )


@pytest.mark.functional
@pytest.mark.order(358)
def test_dns_smd_unreachable_cached_resolution(host):
    """TC-09: pause SMD briefly; CoreDNS must keep serving cached records."""
    verify_pxeboot(
        host,
        "dns_smd_unreachable_cached_resolution",
        check_dns_smd_unreachable_cached_resolution,
    )
