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
    check_hpc_benchmarks_container_first_guidance,
    check_hpc_benchmarks_nfs_accessibility,
    check_hpc_benchmarks_source_only_delivery,
)

from fvt.result import verify_pxeboot

pytestmark = [pytest.mark.slurm, pytest.mark.non_disruptive]


@pytest.mark.sanity
@pytest.mark.order(338)
def test_hpc_benchmarks_container_first_guidance(host):
    """TC-06: Verify pull_benchmarks.sh and benchmark_tools.list are deployed.

    Narrowed from the 2.2 container-first (HPL/HPL-MxP/STREAM) contract to the
    deployment contract actually enforced by hpc_tools.yml. See the check
    function's docstring for the rationale.
    """
    verify_pxeboot(
        host,
        "hpc_benchmarks_container_first_guidance",
        check_hpc_benchmarks_container_first_guidance,
    )


@pytest.mark.sanity
@pytest.mark.order(339)
def test_hpc_benchmarks_source_only_delivery(host):
    """TC-07: Verify no compile/build commands are staged with the artifacts."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_source_only_delivery",
        check_hpc_benchmarks_source_only_delivery,
    )


@pytest.mark.sanity
@pytest.mark.order(340)
def test_hpc_benchmarks_nfs_accessibility(host):
    """TC-10: Verify /hpc_tools NFS is mounted and readable on compute nodes."""
    verify_pxeboot(
        host, "hpc_benchmarks_nfs_accessibility", check_hpc_benchmarks_nfs_accessibility
    )
