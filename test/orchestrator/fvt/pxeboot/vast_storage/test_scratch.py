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

"""VAST scratch directory isolation and LDAP user tests
(TC-003, TC-005, TC-006, TC-007, TC-008)."""

import pytest

from fvt.result import verify_pxeboot
from library.functions import (
    check_vast_scratch_hostname_isolation,
    check_vast_ldapuser_scratch_directory,
    check_vast_ldapuser_subdirectories,
    check_vast_ldapuser_permissions,
    check_vast_scratch_isolation,
)


@pytest.mark.sanity
@pytest.mark.order(702)
@pytest.mark.vast_scratch
def test_vast_scratch_hostname_isolation(host):
    """TC-003: Verify /scratch/<hostname>/ per node; file isolation."""
    verify_pxeboot(
        host, "vast_scratch_hostname_isolation",
        check_vast_scratch_hostname_isolation,
    )


@pytest.mark.sanity
@pytest.mark.order(704)
@pytest.mark.vast_scratch
def test_vast_ldapuser_scratch_directory(host):
    """TC-005: Verify /scratch/<ldapuser>/ on login_compiler nodes."""
    verify_pxeboot(
        host, "vast_ldapuser_scratch_directory",
        check_vast_ldapuser_scratch_directory,
    )


@pytest.mark.sanity
@pytest.mark.order(705)
@pytest.mark.vast_scratch
def test_vast_ldapuser_subdirectories(host):
    """TC-006: Verify data/, jobs/, results/, tmp/ subdirectories."""
    verify_pxeboot(
        host, "vast_ldapuser_subdirectories",
        check_vast_ldapuser_subdirectories,
    )


@pytest.mark.sanity
@pytest.mark.order(706)
@pytest.mark.vast_scratch
def test_vast_ldapuser_permissions(host):
    """TC-007: Verify cross-user permission isolation."""
    verify_pxeboot(
        host, "vast_ldapuser_permissions",
        check_vast_ldapuser_permissions,
    )


@pytest.mark.sanity
@pytest.mark.order(707)
@pytest.mark.vast_scratch
def test_vast_scratch_isolation(host):
    """TC-008: Verify file isolation between scratch subdirectories."""
    verify_pxeboot(host, "vast_scratch_isolation", check_vast_scratch_isolation)
