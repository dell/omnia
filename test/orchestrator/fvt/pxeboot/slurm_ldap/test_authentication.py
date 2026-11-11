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

"""Slurm LDAP authentication and pam_slurm_adopt policy contracts."""

import pytest
from library.functions import (
    TestLogger,
    check_slurm_compiler_ldap_authentication,
    check_slurm_compiler_ldap_invalid_password,
    check_slurm_control_ldap_authentication,
    check_slurm_control_ldap_invalid_password,
    check_slurm_invalid_ldap_identity,
    check_slurm_login_ldap_authentication,
    check_slurm_login_ldap_invalid_password,
    check_slurm_pam_no_job_access,
    check_slurm_pam_policy,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41303)
def test_slurm_pam_policy(host):
    """Verify SSHD, the PAM module, and pam_slurm_adopt account policy."""
    tc = TC["slurm_pam"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_pam_policy)


@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41304)
def test_slurm_control_ldap_authentication(host):
    """Verify a valid LDAP password on the Slurm control node."""
    tc = TC["slurm_control_ldap_auth"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_control_ldap_authentication)


@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.negative
@pytest.mark.order(41305)
def test_slurm_control_ldap_invalid_password(host):
    """Verify an invalid LDAP password is rejected on the control node."""
    tc = TC["slurm_control_ldap_invalid_password"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_control_ldap_invalid_password)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41306)
def test_slurm_login_ldap_authentication(host):
    """Verify a valid LDAP password on every mapped login node."""
    tc = TC["slurm_login_ldap_auth"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_login_ldap_authentication)


@pytest.mark.buildstream
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.negative
@pytest.mark.order(41307)
def test_slurm_login_ldap_invalid_password(host):
    """Verify an invalid LDAP password is rejected on every login node."""
    tc = TC["slurm_login_ldap_invalid_password"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_login_ldap_invalid_password)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41308)
def test_slurm_compiler_ldap_authentication(host):
    """Verify a valid LDAP password on every login-compiler node."""
    tc = TC["slurm_compiler_ldap_auth"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_compiler_ldap_authentication)


@pytest.mark.buildstream
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.negative
@pytest.mark.order(41309)
def test_slurm_compiler_ldap_invalid_password(host):
    """Verify invalid LDAP passwords are rejected on login-compiler nodes."""
    tc = TC["slurm_compiler_ldap_invalid_password"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_compiler_ldap_invalid_password)


@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.negative
@pytest.mark.order(41310)
def test_slurm_pam_no_job_access(host):
    """Verify LDAP compute login is denied without an active job."""
    tc = TC["slurm_pam_no_job"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_pam_no_job_access)


@pytest.mark.buildstream
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.negative
@pytest.mark.order(41311)
def test_slurm_invalid_ldap_identity(host):
    """Verify a generated missing directory identity is rejected."""
    tc = TC["slurm_invalid_ldap"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_invalid_ldap_identity)
