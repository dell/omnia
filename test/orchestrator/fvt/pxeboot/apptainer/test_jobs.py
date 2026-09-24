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

"""Opt-in Apptainer and Slurm workload integration contracts."""

import pytest
from library.functions import (
    check_apptainer_concurrent_jobs,
    check_apptainer_job_array,
    check_apptainer_ldap_job,
    check_apptainer_multi_node_job,
    check_apptainer_nfs_visibility,
    check_apptainer_single_node_job,
    check_apptainer_slurm_environment,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.apptainer,
    pytest.mark.sanity,
    pytest.mark.functional,
    pytest.mark.non_disruptive,
]


@pytest.mark.order(280)
def test_apptainer_single_node_job(host):
    """Run one exact-node container job on every mapped compute."""
    verify_pxeboot(host, "apptainer_single_node_job", check_apptainer_single_node_job)


@pytest.mark.order(281)
def test_apptainer_multi_node_job(host):
    """Run one container allocation spanning all mapped computes."""
    verify_pxeboot(host, "apptainer_multi_node_job", check_apptainer_multi_node_job)


@pytest.mark.order(282)
def test_apptainer_ldap_job(host):
    """Run targeted container jobs as the configured LDAP test identity."""
    verify_pxeboot(host, "apptainer_ldap_job", check_apptainer_ldap_job)


@pytest.mark.order(283)
def test_apptainer_concurrent_jobs(host):
    """Run bounded concurrent container jobs on distinct computes."""
    verify_pxeboot(host, "apptainer_concurrent_jobs", check_apptainer_concurrent_jobs)


@pytest.mark.order(286)
def test_apptainer_nfs_visibility(host):
    """Verify containers can read the shared image path on every compute."""
    verify_pxeboot(host, "apptainer_nfs_visibility", check_apptainer_nfs_visibility)


@pytest.mark.order(287)
def test_apptainer_slurm_environment(host):
    """Verify Slurm allocation variables propagate into containers."""
    verify_pxeboot(
        host, "apptainer_slurm_environment", check_apptainer_slurm_environment
    )


@pytest.mark.order(288)
def test_apptainer_job_array(host):
    """Submit and wait for a bounded Apptainer Slurm job array."""
    verify_pxeboot(host, "apptainer_job_array", check_apptainer_job_array)
