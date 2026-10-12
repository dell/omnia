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

"""VAST scratch directory isolation and LDAP user tests."""

import pytest

from library.functions import (
    TestLogger,
    check_vast_ldapuser_permissions,
    check_vast_ldapuser_scratch_directory,
    check_vast_ldapuser_subdirectories,
    check_vast_scratch_hostname_isolation,
    check_vast_scratch_isolation,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.sanity
@pytest.mark.vast_scratch
@pytest.mark.order(42103)
def test_vast_scratch_hostname_isolation(host):
    """Verify /scratch/<hostname>/ per node; file isolation."""
    tc = TC["vast_scratch_hostname_isolation"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_scratch_hostname_isolation)


@pytest.mark.sanity
@pytest.mark.vast_scratch
@pytest.mark.order(42105)
def test_vast_ldapuser_scratch_directory(host):
    """Verify /scratch/<ldapuser>/ on login_compiler nodes."""
    tc = TC["vast_ldapuser_scratch_directory"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_ldapuser_scratch_directory)


@pytest.mark.sanity
@pytest.mark.vast_scratch
@pytest.mark.order(42106)
def test_vast_ldapuser_subdirectories(host):
    """Verify data/, jobs/, results/, tmp/ subdirectories."""
    tc = TC["vast_ldapuser_subdirectories"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_ldapuser_subdirectories)


@pytest.mark.sanity
@pytest.mark.vast_scratch
@pytest.mark.order(42107)
def test_vast_ldapuser_permissions(host):
    """Verify cross-user permission isolation."""
    tc = TC["vast_ldapuser_permissions"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_ldapuser_permissions)


@pytest.mark.sanity
@pytest.mark.vast_scratch
@pytest.mark.order(42108)
def test_vast_scratch_isolation(host):
    """Verify file isolation between scratch subdirectories."""
    tc = TC["vast_scratch_isolation"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_scratch_isolation)
