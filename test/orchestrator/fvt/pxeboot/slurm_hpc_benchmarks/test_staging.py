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
    check_hpc_benchmarks_artifact_copy,
    check_hpc_benchmarks_json_declaration,
    check_hpc_benchmarks_local_repo_sync,
    check_hpc_benchmarks_msr_safe_arch_boundary,
    check_hpc_benchmarks_post_staging_validation,
    check_hpc_benchmarks_rhel_compatibility,
    check_hpc_benchmarks_tools_dir_creation,
)

from fvt.result import verify_pxeboot

pytestmark = [pytest.mark.slurm, pytest.mark.non_disruptive]


@pytest.mark.sanity
@pytest.mark.order(331)
def test_hpc_benchmarks_json_declaration(host):
    """TC-01: Verify benchmark_tools.list is deployed and non-empty per arch."""
    verify_pxeboot(
        host, "hpc_benchmarks_json_declaration", check_hpc_benchmarks_json_declaration
    )


@pytest.mark.sanity
@pytest.mark.order(332)
def test_hpc_benchmarks_local_repo_sync(host):
    """TC-02: Verify each declared tool has files under the Pulp offline URL."""
    verify_pxeboot(
        host, "hpc_benchmarks_local_repo_sync", check_hpc_benchmarks_local_repo_sync
    )


@pytest.mark.sanity
@pytest.mark.order(333)
def test_hpc_benchmarks_tools_dir_creation(host):
    """TC-03: Verify /hpc_tools directory layout and 0755 permissions."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_tools_dir_creation",
        check_hpc_benchmarks_tools_dir_creation,
    )


@pytest.mark.sanity
@pytest.mark.order(334)
def test_hpc_benchmarks_artifact_copy(host):
    """TC-04: Verify declared benchmark artifacts are staged per tool."""
    verify_pxeboot(
        host, "hpc_benchmarks_artifact_copy", check_hpc_benchmarks_artifact_copy
    )


@pytest.mark.sanity
@pytest.mark.order(335)
def test_hpc_benchmarks_msr_safe_arch_boundary(host):
    """TC-05: Verify msr-safe is staged only for x86_64 nodes."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_msr_safe_arch_boundary",
        check_hpc_benchmarks_msr_safe_arch_boundary,
    )


@pytest.mark.sanity
@pytest.mark.order(336)
def test_hpc_benchmarks_post_staging_validation(host):
    """TC-12: Verify post-staging validation of benchmark tool directories."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_post_staging_validation",
        check_hpc_benchmarks_post_staging_validation,
    )


@pytest.mark.sanity
@pytest.mark.order(337)
def test_hpc_benchmarks_rhel_compatibility(host):
    """TC-13: Verify every compute node runs the targeted RHEL major."""
    verify_pxeboot(
        host, "hpc_benchmarks_rhel_compatibility", check_hpc_benchmarks_rhel_compatibility
    )
