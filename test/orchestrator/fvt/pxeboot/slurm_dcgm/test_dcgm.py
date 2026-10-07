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
from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.sanity,
    pytest.mark.slurm,
    pytest.mark.non_disruptive,
]


# -- CUDA installation checks ------------------------------------------------

@pytest.mark.order(300)
def test_dcgm_cuda_validation(host):
    """Verify NVIDIA driver and CUDA toolkit are installed on GPU nodes."""
    verify_pxeboot(host, "dcgm_cuda_validation", check_dcgm_cuda_validation)


@pytest.mark.order(301)
def test_dcgm_cuda_atomic_lock(host):
    """Verify CUDA toolkit is installed to /hpc_tools/cuda via atomic lock."""
    verify_pxeboot(host, "dcgm_cuda_atomic_lock", check_dcgm_cuda_atomic_lock)


@pytest.mark.order(302)
def test_dcgm_cuda_compute_node(host):
    """Verify both CUDA toolkit and CUDA driver on compute nodes."""
    verify_pxeboot(host, "dcgm_cuda_compute_node", check_dcgm_cuda_compute_node)


@pytest.mark.order(303)
def test_dcgm_cuda_login_compiler(host):
    """Verify CUDA toolkit accessible on login_compiler nodes."""
    verify_pxeboot(host, "dcgm_cuda_login_compiler", check_dcgm_cuda_login_compiler)


# -- DCGM service and package checks -----------------------------------------

@pytest.mark.order(304)
def test_dcgm_package_installed(host):
    """Verify datacenter-gpu-manager RPM and dcgmi binary on GPU nodes."""
    verify_pxeboot(host, "dcgm_package_installed", check_dcgm_package_installed)


@pytest.mark.order(305)
def test_dcgm_daemon_running(host):
    """Verify nvidia-dcgm service is active and enabled on GPU nodes."""
    verify_pxeboot(host, "dcgm_daemon_running", check_dcgm_daemon_running)


# -- GPU discovery and monitoring checks --------------------------------------

@pytest.mark.order(306)
def test_dcgm_gpu_discovery(host):
    """Verify dcgmi discovery enumerates GPUs with unique UUIDs."""
    verify_pxeboot(host, "dcgm_gpu_discovery", check_dcgm_gpu_discovery)


@pytest.mark.order(307)
def test_dcgm_gpu_metrics(host):
    """Verify dcgmi dmon returns metric samples for each GPU node."""
    verify_pxeboot(host, "dcgm_gpu_metrics", check_dcgm_gpu_metrics)


@pytest.mark.order(308)
def test_dcgm_multi_gpu_discovery(host):
    """Verify dcgmi discovery on multi-GPU nodes."""
    verify_pxeboot(host, "dcgm_multi_gpu_discovery", check_dcgm_multi_gpu_discovery)


# -- Multi-node configuration checks -----------------------------------------

@pytest.mark.order(309)
def test_dcgm_multi_gpu_no_login_compiler(host):
    """Verify GPU nodes work without login_compiler present."""
    verify_pxeboot(
        host,
        "dcgm_multi_gpu_no_login_compiler",
        check_dcgm_multi_gpu_no_login_compiler,
    )


@pytest.mark.order(310)
def test_dcgm_multi_login_compiler_lock(host):
    """Verify CUDA toolkit install uses atomic lock with multiple login_compilers."""
    verify_pxeboot(
        host,
        "dcgm_multi_login_compiler_lock",
        check_dcgm_multi_login_compiler_lock,
    )


# -- Platform compatibility checks -------------------------------------------

@pytest.mark.order(311)
def test_dcgm_toolkit_nfs_storage(host):
    """Verify /hpc_tools is NFS-mounted and CUDA toolkit accessible."""
    verify_pxeboot(host, "dcgm_toolkit_nfs_storage", check_dcgm_toolkit_nfs_storage)


@pytest.mark.order(312)
def test_dcgm_rhel_compatibility(host):
    """Verify GPU node OS is a supported RHEL version."""
    verify_pxeboot(host, "dcgm_rhel_compatibility", check_dcgm_rhel_compatibility)


@pytest.mark.order(313)
def test_dcgm_cuda_version_compatibility(host):
    """Verify CUDA toolkit and DCGM daemon version compatibility."""
    verify_pxeboot(
        host,
        "dcgm_cuda_version_compatibility",
        check_dcgm_cuda_version_compatibility,
    )
