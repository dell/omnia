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

"""Slurm LDAP authentication and pam_slurm_adopt policy validation."""

import pytest
from library.functions import (
    check_slurm_compiler_ldap_authentication,
    check_slurm_compiler_ldap_invalid_password,
    check_slurm_compiler_ldap_jobs,
    check_slurm_compiler_pam_job_access,
    check_slurm_control_ldap_authentication,
    check_slurm_control_ldap_invalid_password,
    check_slurm_control_ldap_jobs,
    check_slurm_control_pam_job_access,
    check_slurm_invalid_ldap_identity,
    check_slurm_login_ldap_authentication,
    check_slurm_login_ldap_invalid_password,
    check_slurm_login_ldap_jobs,
    check_slurm_login_pam_job_access,
    check_slurm_pam_no_job_access,
)

from fvt.result import verify_pxeboot

pytestmark = pytest.mark.non_disruptive


@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(233)
def test_slurm_control_ldap_authentication(host):
    """Verify a valid LDAP password on the Slurm control node."""
    verify_pxeboot(
        host,
        "slurm_control_ldap_auth",
        check_slurm_control_ldap_authentication,
    )


@pytest.mark.negative
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(234)
def test_slurm_control_ldap_invalid_password(host):
    """Verify an invalid LDAP password is rejected on the control node."""
    verify_pxeboot(
        host,
        "slurm_control_ldap_invalid_password",
        check_slurm_control_ldap_invalid_password,
    )


@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(235)
def test_slurm_login_ldap_authentication(host):
    """Verify a valid LDAP password on every mapped login node."""
    verify_pxeboot(
        host,
        "slurm_login_ldap_auth",
        check_slurm_login_ldap_authentication,
    )


@pytest.mark.negative
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(236)
def test_slurm_login_ldap_invalid_password(host):
    """Verify an invalid LDAP password is rejected on every login node."""
    verify_pxeboot(
        host,
        "slurm_login_ldap_invalid_password",
        check_slurm_login_ldap_invalid_password,
    )


@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(237)
def test_slurm_compiler_ldap_authentication(host):
    """Verify a valid LDAP password on every login-compiler node."""
    verify_pxeboot(
        host,
        "slurm_compiler_ldap_auth",
        check_slurm_compiler_ldap_authentication,
    )


@pytest.mark.negative
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(238)
def test_slurm_compiler_ldap_invalid_password(host):
    """Verify invalid LDAP passwords are rejected on login-compiler nodes."""
    verify_pxeboot(
        host,
        "slurm_compiler_ldap_invalid_password",
        check_slurm_compiler_ldap_invalid_password,
    )


@pytest.mark.negative
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(239)
def test_slurm_pam_no_job_access(host):
    """Verify LDAP compute login is denied without an active job."""
    verify_pxeboot(host, "slurm_pam_no_job", check_slurm_pam_no_job_access)


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(240)
def test_slurm_control_ldap_jobs(host):
    """Submit and complete an LDAP-owned job from the control node."""
    verify_pxeboot(host, "slurm_control_ldap_jobs", check_slurm_control_ldap_jobs)


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(241)
def test_slurm_control_pam_job_access(host):
    """Verify control-submitted PAM access during and after a job."""
    verify_pxeboot(
        host,
        "slurm_control_pam_job_access",
        check_slurm_control_pam_job_access,
    )


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(242)
def test_slurm_login_ldap_jobs(host):
    """Submit and complete an LDAP-owned job from every login node."""
    verify_pxeboot(host, "slurm_login_ldap_jobs", check_slurm_login_ldap_jobs)


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(243)
def test_slurm_login_pam_job_access(host):
    """Verify login-node PAM access during and after a job."""
    verify_pxeboot(
        host,
        "slurm_login_pam_job_access",
        check_slurm_login_pam_job_access,
    )


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(244)
def test_slurm_compiler_ldap_jobs(host):
    """Submit an LDAP-owned job from every login-compiler node."""
    verify_pxeboot(host, "slurm_compiler_ldap_jobs", check_slurm_compiler_ldap_jobs)


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(245)
def test_slurm_compiler_pam_job_access(host):
    """Verify login-compiler PAM access during and after a job."""
    verify_pxeboot(
        host,
        "slurm_compiler_pam_job_access",
        check_slurm_compiler_pam_job_access,
    )


@pytest.mark.negative
@pytest.mark.sanity
@pytest.mark.openldap
@pytest.mark.slurm
@pytest.mark.order(246)
def test_slurm_invalid_ldap_identity(host):
    """Verify a generated missing directory identity is rejected."""
    verify_pxeboot(host, "slurm_invalid_ldap", check_slurm_invalid_ldap_identity)
