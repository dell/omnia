# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""End-to-end Slurm GPU, CUDA, GRES, and DCGM verification."""

import posixpath

import pytest

from fvt.check.feature_helpers import (
    read_remote_yaml,
    run_node_command,
    slurm_node_ips,
    target_paths,
)
from library.functions.slurm_func import (
    get_node_ip_from_pxe_mapping,
    get_slurm_control_nodes,
)


pytestmark = [pytest.mark.slurm, pytest.mark.gpu, pytest.mark.functional]


def _gpu_nodes(host):
    gpu_nodes = []
    for name, address in slurm_node_ips(host, include_control=False):
        result = run_node_command(host, address, "nvidia-smi -L")
        if result.rc == 0 and "GPU" in result.stdout:
            gpu_nodes.append((name, address))
    if not gpu_nodes:
        pytest.skip("No NVIDIA GPU nodes are configured in this Slurm cluster")
    return gpu_nodes


@pytest.mark.order(50)
def test_gpu_driver_and_cuda_available(host):
    """ORCH_FVT_GPU_V001: NVIDIA driver and CUDA runtime work on every GPU node."""
    failures = []
    for name, address in _gpu_nodes(host):
        result = run_node_command(
            host,
            address,
            "nvidia-smi -L && test -d /usr/local/cuda && "
            "test -s /etc/profile.d/cuda.sh",
        )
        if result.rc != 0:
            failures.append(name)
    assert not failures, f"GPU/CUDA setup failed on nodes: {failures}"


@pytest.mark.order(51)
def test_slurm_gres_matches_detected_gpus(host):
    """ORCH_FVT_GPU_V002: Slurm exposes a GPU GRES on every detected GPU node."""
    gpu_names = {name for name, _address in _gpu_nodes(host)}
    control_nodes = get_slurm_control_nodes(host)
    assert control_nodes, "No Slurm control node is configured"
    control_ip = get_node_ip_from_pxe_mapping(host, control_nodes[0])
    assert control_ip, "Slurm control node has no administrative IP"
    result = run_node_command(host, control_ip, "sinfo -N -h -o '%N|%G'")
    assert result.rc == 0, f"Unable to query Slurm GRES: {result.stderr}"
    gres_by_node = {}
    for line in result.stdout.splitlines():
        if "|" in line:
            node_name, gres = line.split("|", 1)
            gres_by_node[node_name.strip()] = gres.strip().lower()
    missing = sorted(
        name for name in gpu_names if "gpu" not in gres_by_node.get(name, "")
    )
    assert not missing, f"Detected GPU nodes missing Slurm GRES: {missing}"


@pytest.mark.order(52)
def test_dcgm_active_when_enabled(host):
    """ORCH_FVT_GPU_V003: DCGM is active on GPU nodes when configured."""
    config_path = posixpath.join(
        target_paths()["input"], "orchestrator_config.yml"
    )
    config = read_remote_yaml(host, config_path)
    if not config.get("dcgm_enabled", True):
        pytest.skip("DCGM is disabled in orchestrator_config.yml")
    failures = []
    for name, address in _gpu_nodes(host):
        result = run_node_command(
            host, address, "systemctl is-active nvidia-dcgm"
        )
        if result.rc != 0 or result.stdout.strip() != "active":
            failures.append(name)
    assert not failures, f"nvidia-dcgm is inactive on GPU nodes: {failures}"


@pytest.mark.order(53)
def test_slurm_gpu_job_completes(host):
    """ORCH_FVT_GPU_V004: Slurm allocates a GPU and completes nvidia-smi."""
    _gpu_nodes(host)
    control_nodes = get_slurm_control_nodes(host)
    assert control_nodes, "No Slurm control node is configured"
    control_ip = get_node_ip_from_pxe_mapping(host, control_nodes[0])
    assert control_ip, "Slurm control node has no administrative IP"
    result = run_node_command(
        host,
        control_ip,
        "timeout 180 srun --nodes=1 --ntasks=1 --gres=gpu:1 nvidia-smi -L",
        15,
    )
    assert result.rc == 0 and "GPU" in result.stdout, (
        f"Slurm GPU workload failed: rc={result.rc} stderr={result.stderr}"
    )
