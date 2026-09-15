# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Live verification of Apptainer installation and offline image support."""

import shlex

import pytest

from fvt.check.feature_helpers import (
    run_node_command,
    slurm_data_node_ips,
    slurm_node_ips,
)


pytestmark = [pytest.mark.apptainer, pytest.mark.functional]


@pytest.mark.order(40)
def test_apptainer_installed_on_slurm_nodes(host):
    """ORCH_FVT_APPTAINER_V001: Apptainer is executable on every configured Slurm node."""
    failures = []
    for name, address in slurm_node_ips(host):
        result = run_node_command(host, address, "apptainer --version")
        if result.rc != 0 or "apptainer" not in result.stdout.lower():
            failures.append(name)
    assert not failures, f"Apptainer is unavailable on Slurm nodes: {failures}"


@pytest.mark.order(41)
def test_apptainer_registry_mirror_configured(host):
    """ORCH_FVT_APPTAINER_V002: Apptainer/containers registry config points to a mirror."""
    failures = []
    for name, address in slurm_node_ips(host):
        result = run_node_command(
            host,
            address,
            "test -s /etc/containers/registries.conf.d/apptainer_mirror.conf && "
            "cat /etc/containers/registries.conf.d/apptainer_mirror.conf",
        )
        content = result.stdout
        if result.rc != 0 or "[[registry.mirror]]" not in content:
            failures.append(name)
            continue
        for registry in (
            "docker.io",
            "ghcr.io",
            "quay.io",
            "registry.k8s.io",
            "nvcr.io",
            "public.ecr.aws",
            "gcr.io",
        ):
            if registry not in content:
                failures.append(f"{name} ({registry})")
    assert not failures, f"Invalid Apptainer mirror configuration: {failures}"


@pytest.mark.order(42)
def test_apptainer_image_download_assets_installed(host):
    """ORCH_FVT_APPTAINER_V003: Offline image downloader and image list are installed."""
    name, address = slurm_data_node_ips(host)[0]
    result = run_node_command(
        host,
        address,
        "test -x /hpc_tools/scripts/download_container_image.sh && "
        "test -s /hpc_tools/scripts/container_image.list && "
        "grep -v '^[[:space:]]*#' /hpc_tools/scripts/container_image.list",
    )
    assert result.rc == 0, f"Apptainer image assets missing on {name}: {result.stderr}"
    assert "nvcr.io/nvidia/hpc-benchmarks" in result.stdout


@pytest.mark.order(43)
def test_apptainer_sif_smoke_execution(host):
    """ORCH_FVT_APPTAINER_V004: A staged SIF image executes without network access."""
    name, address = slurm_data_node_ips(host)[0]
    find_result = run_node_command(
        host,
        address,
        "if test -d /hpc_tools/container_images; then "
        "find /hpc_tools/container_images -maxdepth 1 -type f -name '*.sif' "
        "-size +0c -print -quit 2>/dev/null; fi",
    )
    assert find_result.rc == 0, f"Unable to inspect SIF images on {name}"
    image = find_result.stdout.strip()
    if not image:
        pytest.skip("No SIF image has been staged for an Apptainer smoke test")
    inspect_result = run_node_command(
        host, address, f"timeout 120 apptainer inspect {shlex.quote(image)}"
    )
    assert inspect_result.rc == 0, (
        f"Apptainer could not inspect SIF on {name}: {inspect_result.stderr}"
    )
    result = run_node_command(
        host,
        address,
        f"timeout 120 apptainer exec --containall {shlex.quote(image)} true",
        15,
    )
    assert result.rc == 0, (
        f"Apptainer SIF smoke test failed on {name}: {result.stderr}"
    )
