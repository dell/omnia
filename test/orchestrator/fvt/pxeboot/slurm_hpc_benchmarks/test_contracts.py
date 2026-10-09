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

"""HPC benchmarks declarative and shared-storage contracts (non-disruptive)."""

import pytest
from library.functions import (
    TestLogger,
    check_hpc_benchmarks_container_first_guidance,
    check_hpc_benchmarks_container_image_list,
    check_hpc_benchmarks_nfs_accessibility,
    check_hpc_benchmarks_offline_package_copy,
    check_hpc_benchmarks_platform_directory_structure,
    check_hpc_benchmarks_platform_script,
    check_hpc_benchmarks_source_only_delivery,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot

@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42012)
def test_hpc_benchmarks_platform_script(host):
    """TC-06a: Verify omnia_platform.sh deployment and platform detection."""
    tc = TC["hpc_benchmarks_platform_script"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_platform_script)


@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42013)
def test_hpc_benchmarks_container_image_list(host):
    """TC-06b: Verify container_image.list deployment and content validation."""
    tc = TC["hpc_benchmarks_container_image_list"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_container_image_list)


@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42014)
def test_hpc_benchmarks_platform_directory_structure(host):
    """TC-06c: Verify platform-specific directory structure exists per architecture."""
    tc = TC["hpc_benchmarks_platform_directory_structure"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_platform_directory_structure)


@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42015)
def test_hpc_benchmarks_offline_package_copy(host):
    """TC-06d: Verify offline packages are copied to slurm_config_path/packages/{arch}/."""
    tc = TC["hpc_benchmarks_offline_package_copy"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_offline_package_copy)


@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42016)
def test_hpc_benchmarks_container_first_guidance(host):
    """TC-06: Verify pull_benchmarks.sh and benchmark_tools.list are deployed.

    Narrowed from the 2.2 container-first (HPL/HPL-MxP/STREAM) contract to the
    deployment contract actually enforced by hpc_tools.yml. See the check
    function's docstring for the rationale.
    """
    tc = TC["hpc_benchmarks_container_first_guidance"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_container_first_guidance)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42017)
def test_hpc_benchmarks_source_only_delivery(host):
    """TC-07: Verify no compile/build commands are staged with the artifacts."""
    tc = TC["hpc_benchmarks_source_only_delivery"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_source_only_delivery)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42018)
def test_hpc_benchmarks_nfs_accessibility(host):
    """TC-10: Verify /hpc_tools NFS is mounted and readable on compute nodes."""
    tc = TC["hpc_benchmarks_nfs_accessibility"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_nfs_accessibility)
