# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Live verification of the shared HPC benchmark toolchain."""

import shlex

import pytest

from fvt.check.feature_helpers import run_node_command, slurm_data_node_ips


pytestmark = [pytest.mark.hpc_benchmarks, pytest.mark.functional]

REQUIRED_BENCHMARKS = {
    "osu-micro-benchmarks",
    "imb",
    "likwid",
    "papi",
    "geopm",
    "sionlib",
    "msr-safe",
}


def _first_slurm_node(host):
    return slurm_data_node_ips(host)[0]


@pytest.mark.order(30)
def test_hpc_tools_share_available_on_slurm_nodes(host):
    """ORCH_FVT_HPC_BENCHMARKS_V001: Every Slurm data node can access the HPC tool path."""
    failures = []
    for name, address in slurm_data_node_ips(host):
        result = run_node_command(
            host, address,
            "mountpoint -q /hpc_tools && test -d /hpc_tools/scripts",
        )
        if result.rc != 0:
            failures.append(name)
    assert not failures, f"/hpc_tools is unavailable on Slurm data nodes: {failures}"


@pytest.mark.order(31)
def test_benchmark_staging_assets_installed(host):
    """ORCH_FVT_HPC_BENCHMARKS_V002: Benchmark downloader and allowlist are deployed safely."""
    name, address = _first_slurm_node(host)
    result = run_node_command(
        host,
        address,
        "test -x /hpc_tools/scripts/pull_benchmarks.sh && "
        "test -s /hpc_tools/scripts/benchmark_tools.list && "
        "cat /hpc_tools/scripts/benchmark_tools.list",
    )
    assert result.rc == 0, f"Benchmark staging assets missing on {name}: {result.stderr}"
    configured = {
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert REQUIRED_BENCHMARKS <= configured, (
        f"Missing benchmark definitions: {sorted(REQUIRED_BENCHMARKS - configured)}"
    )


@pytest.mark.order(32)
def test_staged_benchmark_artifacts_are_nonempty(host):
    """ORCH_FVT_HPC_BENCHMARKS_V003: Any staged benchmark directory contains usable artifacts."""
    name, address = _first_slurm_node(host)
    present = run_node_command(
        host,
        address,
        "for d in /hpc_tools/osu-micro-benchmarks /hpc_tools/imb "
        "/hpc_tools/likwid /hpc_tools/papi /hpc_tools/geopm /hpc_tools/sionlib; "
        "do if test -d \"$d\"; then find \"$d\" -type f -print -quit; fi; done",
    )
    assert present.rc == 0, f"Unable to inspect benchmark artifacts on {name}"
    if not present.stdout.strip():
        pytest.skip("Benchmark artifacts have not been pulled to the shared path")
    empty = run_node_command(
        host,
        address,
        "find /hpc_tools/osu-micro-benchmarks /hpc_tools/imb "
        "/hpc_tools/likwid /hpc_tools/papi /hpc_tools/geopm /hpc_tools/sionlib "
        "-type f -empty -print -quit 2>/dev/null",
    )
    assert empty.rc == 0 and not empty.stdout.strip(), (
        f"Empty benchmark artifact on {name}: {empty.stdout.strip()}"
    )


@pytest.mark.order(33)
def test_benchmark_executables_can_start(host):
    """ORCH_FVT_HPC_BENCHMARKS_V004: A staged OSU or IMB benchmark executable can start."""
    name, address = _first_slurm_node(host)
    find_result = run_node_command(
        host,
        address,
        "for d in /hpc_tools/osu-micro-benchmarks /hpc_tools/imb; do "
        "if test -d \"$d\"; then find \"$d\" -type f "
        "\\( -name osu_latency -o -name IMB-MPI1 \\) -perm /111 "
        "-print -quit 2>/dev/null; fi; done",
    )
    assert find_result.rc == 0, f"Benchmark executable search failed on {name}"
    executable = find_result.stdout.strip()
    if not executable:
        pytest.skip("No staged OSU/IMB executable is available for a smoke test")
    result = run_node_command(
        host, address, f"timeout 30 {shlex.quote(executable)} --help"
    )
    assert result.rc in {0, 1}, (
        f"Benchmark executable could not start on {name}: rc={result.rc} "
        f"stderr={result.stderr}"
    )
