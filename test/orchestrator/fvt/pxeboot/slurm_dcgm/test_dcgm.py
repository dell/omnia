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

"""DCGM and CUDA functional verification after PXE boot.

Covers the 14 functional validation scenarios from the 2.2 DCGM baseline:
CUDA installation, DCGM service, GPU discovery, monitoring, multi-node
configurations, and platform compatibility.
"""

import pytest

from library.functions import (
    TestLogger,
    check_dcgm_cuda_atomic_lock,
    check_dcgm_cuda_compute_node,
    check_dcgm_cuda_login_compiler,
    check_dcgm_cuda_validation,
    check_dcgm_cuda_version_compatibility,
    check_dcgm_daemon_running,
    check_dcgm_gpu_discovery,
    check_dcgm_gpu_metrics,
    check_dcgm_multi_gpu_discovery,
    check_dcgm_multi_gpu_no_login_compiler,
    check_dcgm_multi_login_compiler_lock,
    check_dcgm_package_installed,
    check_dcgm_rhel_compatibility,
    check_dcgm_toolkit_nfs_storage,
)
from library.vars import TEST_CASES as TC
from fvt.result import verify_pxeboot

# -- CUDA installation checks ------------------------------------------------

@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41501)
def test_dcgm_cuda_validation(host):
    """Verify NVIDIA driver and CUDA toolkit are installed on GPU nodes."""
    tc = TC["dcgm_cuda_validation"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_cuda_validation)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41502)
def test_dcgm_cuda_atomic_lock(host):
    """Verify CUDA toolkit is installed to /hpc_tools/cuda via atomic lock."""
    tc = TC["dcgm_cuda_atomic_lock"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_cuda_atomic_lock)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41503)
def test_dcgm_cuda_compute_node(host):
    """Verify both CUDA toolkit and CUDA driver on compute nodes."""
    tc = TC["dcgm_cuda_compute_node"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_cuda_compute_node)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41504)
def test_dcgm_cuda_login_compiler(host):
    """Verify CUDA toolkit accessible on login_compiler nodes."""
    tc = TC["dcgm_cuda_login_compiler"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_cuda_login_compiler)


# -- DCGM service and package checks -----------------------------------------

@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41505)
def test_dcgm_package_installed(host):
    """Verify datacenter-gpu-manager RPM and dcgmi binary on GPU nodes."""
    tc = TC["dcgm_package_installed"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_package_installed)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41506)
def test_dcgm_daemon_running(host):
    """Verify nvidia-dcgm service is active and enabled on GPU nodes."""
    tc = TC["dcgm_daemon_running"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_daemon_running)


# -- GPU discovery and monitoring checks --------------------------------------

@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41507)
def test_dcgm_gpu_discovery(host):
    """Verify dcgmi discovery enumerates GPUs with unique UUIDs."""
    tc = TC["dcgm_gpu_discovery"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_gpu_discovery)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41508)
def test_dcgm_gpu_metrics(host):
    """Verify dcgmi dmon returns metric samples for each GPU node."""
    tc = TC["dcgm_gpu_metrics"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_gpu_metrics)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41509)
def test_dcgm_multi_gpu_discovery(host):
    """Verify dcgmi discovery on multi-GPU nodes."""
    tc = TC["dcgm_multi_gpu_discovery"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_multi_gpu_discovery)


# -- Multi-node configuration checks -----------------------------------------

@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41510)
def test_dcgm_multi_gpu_no_login_compiler(host):
    """Verify GPU nodes work without login_compiler present."""
    tc = TC["dcgm_multi_gpu_no_login_compiler"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_multi_gpu_no_login_compiler)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41511)
def test_dcgm_multi_login_compiler_lock(host):
    """Verify CUDA toolkit install uses atomic lock with multiple login_compilers."""
    tc = TC["dcgm_multi_login_compiler_lock"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_multi_login_compiler_lock)


# -- Platform compatibility checks -------------------------------------------

@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41512)
def test_dcgm_toolkit_nfs_storage(host):
    """Verify /hpc_tools is NFS-mounted and CUDA toolkit accessible."""
    tc = TC["dcgm_toolkit_nfs_storage"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_toolkit_nfs_storage)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41513)
def test_dcgm_rhel_compatibility(host):
    """Verify GPU node OS is a supported RHEL version."""
    tc = TC["dcgm_rhel_compatibility"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_rhel_compatibility)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41514)
def test_dcgm_cuda_version_compatibility(host):
    """Verify CUDA toolkit and DCGM daemon version compatibility."""
    tc = TC["dcgm_cuda_version_compatibility"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_dcgm_cuda_version_compatibility)
