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

"""External LDAP proxy setup that LDAP login checks depend on.

These cases run first in the slurm_ldap suite. Prepare only starts the local
omnia_auth container, so pointing it at the external directory belongs here,
immediately before the LDAP authentication and job cases.
"""

import pytest
from library.functions import (
    TestLogger,
    check_external_ldap_backend,
    reconcile_external_ldap_proxy,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41301)
def test_external_ldap_proxy(host):
    """Reconcile and verify the explicitly enabled LDAP meta-proxy."""
    tc = TC["external_ldap_proxy"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, reconcile_external_ldap_proxy)


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41302)
def test_external_ldap_backend(host):
    """Verify external LDAP reachability from the omnia_auth container."""
    tc = TC["external_ldap_backend"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_external_ldap_backend)
