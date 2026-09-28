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

"""LDAP-owned Slurm jobs and pam_slurm_adopt access lifecycles."""

import pytest
from library.functions import (
    check_slurm_compiler_ldap_jobs,
    check_slurm_compiler_pam_job_access,
    check_slurm_control_ldap_jobs,
    check_slurm_control_pam_job_access,
    check_slurm_login_ldap_jobs,
    check_slurm_login_pam_job_access,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.functional,
    pytest.mark.sanity,
    pytest.mark.openldap,
    pytest.mark.slurm,
    pytest.mark.non_disruptive,
]


@pytest.mark.order(248)
def test_slurm_control_ldap_jobs(host):
    """Submit and complete an LDAP-owned job from the control node."""
    verify_pxeboot(host, "slurm_control_ldap_jobs", check_slurm_control_ldap_jobs)


@pytest.mark.order(249)
def test_slurm_control_pam_job_access(host):
    """Verify control-submitted PAM access during and after a job."""
    verify_pxeboot(
        host,
        "slurm_control_pam_job_access",
        check_slurm_control_pam_job_access,
    )


@pytest.mark.order(250)
def test_slurm_login_ldap_jobs(host):
    """Submit and complete an LDAP-owned job from every login node."""
    verify_pxeboot(host, "slurm_login_ldap_jobs", check_slurm_login_ldap_jobs)


@pytest.mark.order(251)
def test_slurm_login_pam_job_access(host):
    """Verify login-node PAM access during and after a job."""
    verify_pxeboot(
        host,
        "slurm_login_pam_job_access",
        check_slurm_login_pam_job_access,
    )


@pytest.mark.order(252)
def test_slurm_compiler_ldap_jobs(host):
    """Submit an LDAP-owned job from every login-compiler node."""
    verify_pxeboot(host, "slurm_compiler_ldap_jobs", check_slurm_compiler_ldap_jobs)


@pytest.mark.order(253)
def test_slurm_compiler_pam_job_access(host):
    """Verify login-compiler PAM access during and after a job."""
    verify_pxeboot(
        host,
        "slurm_compiler_pam_job_access",
        check_slurm_compiler_pam_job_access,
    )
