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
    TestLogger,
    check_apptainer_concurrent_jobs,
    check_apptainer_job_array,
    check_apptainer_ldap_job,
    check_apptainer_multi_node_job,
    check_apptainer_nfs_visibility,
    check_apptainer_single_node_job,
    check_apptainer_slurm_environment,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.apptainer
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.non_disruptive
@pytest.mark.order(41915)
def test_apptainer_single_node_job(host):
    """Run one exact-node container job on every mapped compute."""
    tc = TC["apptainer_single_node_job"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_single_node_job)


@pytest.mark.apptainer
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.non_disruptive
@pytest.mark.order(41916)
def test_apptainer_multi_node_job(host):
    """Run one container allocation spanning all mapped computes."""
    tc = TC["apptainer_multi_node_job"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_multi_node_job)


@pytest.mark.apptainer
@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.non_disruptive
@pytest.mark.order(41917)
def test_apptainer_ldap_job(host):
    """Run targeted container jobs as the configured LDAP test identity."""
    tc = TC["apptainer_ldap_job"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_ldap_job)


@pytest.mark.apptainer
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.non_disruptive
@pytest.mark.order(41918)
def test_apptainer_concurrent_jobs(host):
    """Run bounded concurrent container jobs on distinct computes."""
    tc = TC["apptainer_concurrent_jobs"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_concurrent_jobs)


@pytest.mark.apptainer
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.non_disruptive
@pytest.mark.order(41921)
def test_apptainer_nfs_visibility(host):
    """Verify containers can read the shared image path on every compute."""
    tc = TC["apptainer_nfs_visibility"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_nfs_visibility)


@pytest.mark.apptainer
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.non_disruptive
@pytest.mark.order(41922)
def test_apptainer_slurm_environment(host):
    """Verify Slurm allocation variables propagate into containers."""
    tc = TC["apptainer_slurm_environment"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_slurm_environment)


@pytest.mark.apptainer
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.non_disruptive
@pytest.mark.order(41923)
def test_apptainer_job_array(host):
    """Submit and wait for a bounded Apptainer Slurm job array."""
    tc = TC["apptainer_job_array"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_apptainer_job_array)
