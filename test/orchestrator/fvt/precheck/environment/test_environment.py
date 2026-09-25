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

"""OIM identity and administrative-address contracts."""

import pytest
from library.functions import (
    check_precheck_admin_ipv4,
    check_precheck_hostname_domain,
)

from fvt.result import verify_precheck

pytestmark = [pytest.mark.sanity]


@pytest.mark.order(1)
def test_precheck_hostname_domain(host):
    """Require the host identity to match omnia.env exactly."""
    verify_precheck(host, "precheck_hostname_domain", check_precheck_hostname_domain)


@pytest.mark.order(2)
def test_precheck_admin_ipv4(host):
    """Require the configured administrative IPv4 on a global interface."""
    verify_precheck(host, "precheck_admin_ipv4", check_precheck_admin_ipv4)
