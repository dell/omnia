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

"""HPC benchmarks staging, layout, and compatibility contracts (non-disruptive)."""

import pytest
from library.functions import (
    TestLogger,
    check_hpc_benchmarks_artifact_copy,
    check_hpc_benchmarks_json_declaration,
    check_hpc_benchmarks_local_repo_sync,
    check_hpc_benchmarks_msr_safe_arch_boundary,
    check_hpc_benchmarks_post_staging_validation,
    check_hpc_benchmarks_rhel_compatibility,
    check_hpc_benchmarks_tools_dir_creation,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot

@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42001)
def test_hpc_benchmarks_json_declaration(host):
    """TC-01: Verify benchmark_tools.list is deployed and non-empty per arch."""
    tc = TC["hpc_benchmarks_json_declaration"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_json_declaration)


@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42002)
def test_hpc_benchmarks_local_repo_sync(host):
    """TC-02: Verify each declared tool has files under the Pulp offline URL."""
    tc = TC["hpc_benchmarks_local_repo_sync"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_local_repo_sync)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42003)
def test_hpc_benchmarks_tools_dir_creation(host):
    """TC-03: Verify /hpc_tools directory layout and 0755 permissions."""
    tc = TC["hpc_benchmarks_tools_dir_creation"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_tools_dir_creation)


@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42004)
def test_hpc_benchmarks_artifact_copy(host):
    """TC-04: Verify declared benchmark artifacts are staged per tool."""
    tc = TC["hpc_benchmarks_artifact_copy"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_artifact_copy)


@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42005)
def test_hpc_benchmarks_msr_safe_arch_boundary(host):
    """TC-05: Verify msr-safe is staged only for x86_64 nodes."""
    tc = TC["hpc_benchmarks_msr_safe_arch_boundary"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_msr_safe_arch_boundary)


@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42006)
def test_hpc_benchmarks_post_staging_validation(host):
    """TC-12: Verify post-staging validation of benchmark tool directories."""
    tc = TC["hpc_benchmarks_post_staging_validation"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_post_staging_validation)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42007)
def test_hpc_benchmarks_rhel_compatibility(host):
    """TC-13: Verify every compute node runs the targeted RHEL major."""
    tc = TC["hpc_benchmarks_rhel_compatibility"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_rhel_compatibility)
