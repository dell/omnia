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

"""
OCI Image Ingest — Boot Validation.

Validates end-to-end PXE boot with OCI image ingest artifacts:
  TC-FVT-034: Successful node boot via PXE with ingested images
  TC-FVT-035: Boot failure attributed to source image

Auto-discovers nodes from the Orchestrator pxe_mapping_file.csv and
verifies they are reachable, running the correct kernel, and that
build_status.yml contains OCI provenance for failure attribution.
"""

import csv
import io
import pytest

from library.functions import (
    TestLogger,
    run_on_host,
    read_remote_env,
)
from library.functions.oci_image_ingest_func import (
    validate_build_status,
)
from library.vars import (
    TEST_CASES as TC,
    OCI_IMAGE_BUILD_TYPE,
)
from library.vars.common_vars import (
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
)
from library.messages import TEST_LOG_MSGS as LOG


def _get_pxe_mapping_path(host) -> str:
    """Build the PXE mapping file path from environment variables.

    Uses OMNIA_DATA_PATH and OMNIA_PROJECT_NAME to construct:
        <OMNIA_DATA_PATH>/orchestrator/input/<OMNIA_PROJECT_NAME>/pxe_mapping_file.csv
    """
    data_path = read_remote_env(host, ENV_OMNIA_DATA_PATH)
    project = read_remote_env(host, ENV_OMNIA_PROJECT_NAME)
    if not data_path or not project:
        return ""
    return f"{data_path}/orchestrator/input/{project}/pxe_mapping_file.csv"


def _load_pxe_nodes(host):
    """Read the PXE mapping file and return a list of node dicts.

    Each dict has keys: functional_group, hostname, admin_ip.
    Returns an empty list if the file does not exist.
    """
    pxe_path = _get_pxe_mapping_path(host)
    if not pxe_path:
        return []
    check = run_on_host(host, f"test -f {pxe_path} && echo exists")
    if "exists" not in check.stdout:
        return []

    raw = run_on_host(host, f"cat {pxe_path}")
    reader = csv.DictReader(io.StringIO(raw.stdout))
    nodes = []
    for row in reader:
        fg = row.get("FUNCTIONAL_GROUP_NAME", "").strip()
        hostname = row.get("HOSTNAME", "").strip()
        ip = row.get("ADMIN_IP", "").strip()
        if fg and ip:
            nodes.append({
                "functional_group": fg,
                "hostname": hostname,
                "admin_ip": ip,
            })
    return nodes


@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(200)
def test_oci_node_boot_success(host):
    """Verify nodes booted via PXE with OCI-ingested images.

    Auto-discovers nodes from pxe_mapping_file.csv, SSHs to each,
    and confirms the running kernel matches the kernel_version
    recorded in build_status.yml.
    """
    tc = TC["oci_node_boot_success"]
    tl = TestLogger(tc["title"], tc["id"])

    # --- build_status ---
    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    status = status_result["status_data"]
    if status.get("image_build_type") != OCI_IMAGE_BUILD_TYPE:
        tl.skipped(f"build_status type is {status.get('image_build_type')}")
        pytest.skip("Not an oci-image-ingest build_status")

    # Build a map: functional_group -> expected kernel_version
    expected_kernels = {}
    for source in status.get("oci_sources", []):
        fg = source.get("functional_group", "")
        kv = source.get("kernel_version", "")
        if fg and kv:
            expected_kernels[fg] = kv

    # --- PXE nodes ---
    nodes = _load_pxe_nodes(host)
    if not nodes:
        tl.skipped("No pxe_mapping_file.csv or no nodes listed")
        pytest.skip("PXE mapping file not found or empty")

    verified = 0
    failures = []
    for node in nodes:
        fg = node["functional_group"]
        ip = node["admin_ip"]
        name = node["hostname"] or ip
        expected_kv = expected_kernels.get(fg, "")
        if not expected_kv:
            continue  # functional group not from OCI ingest

        # SSH to the node and read its running kernel
        ssh_cmd = (
            f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
            f"root@{ip} 'uname -r' 2>/dev/null"
        )
        result = run_on_host(host, ssh_cmd)
        running_kv = result.stdout.strip()

        if running_kv == expected_kv:
            verified += 1
        else:
            failures.append(
                f"{name} ({ip}): expected {expected_kv}, got '{running_kv}'"
            )

    if not verified and not failures:
        tl.skipped("No PXE nodes match OCI ingest functional groups")
        pytest.skip("No matching functional groups in PXE mapping")

    if failures:
        tl.failed(f"Kernel mismatch on {len(failures)} node(s): {failures}")
        assert False, f"Kernel mismatch: {failures}"

    tl.passed(f"All {verified} node(s) running expected kernel from OCI ingest")


@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(201)
def test_oci_boot_failure_attribution(host):
    """Verify OCI provenance is available for boot failure attribution.

    Confirms build_status.yml oci_sources contain digest, registry,
    repository, and kernel_version for every source — the data needed
    to attribute a boot failure back to the source image.
    Also verifies PXE nodes are reachable (proving no boot failure).
    """
    tc = TC["oci_boot_failure_attribution"]
    tl = TestLogger(tc["title"], tc["id"])

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    sources = status_result["status_data"].get("oci_sources", [])
    if not sources:
        tl.skipped("No oci_sources for provenance check")
        pytest.skip("No oci_sources available")

    # Check provenance fields
    for source in sources:
        fg = source.get("functional_group", "?")
        missing = []
        for field in ("digest", "registry", "repository", "kernel_version"):
            if not source.get(field):
                missing.append(field)
        if missing:
            tl.failed(f"Missing provenance for {fg}: {missing}")
            assert False, f"Incomplete provenance for {fg}: {missing}"

    # Verify PXE nodes are reachable (no boot failure)
    nodes = _load_pxe_nodes(host)
    unreachable = []
    for node in nodes:
        ping_cmd = f"ping -c1 -W5 {node['admin_ip']} >/dev/null 2>&1 && echo ok"
        result = run_on_host(host, ping_cmd)
        if "ok" not in result.stdout:
            unreachable.append(f"{node['hostname']} ({node['admin_ip']})")

    if unreachable:
        tl.failed(f"Unreachable nodes (possible boot failure): {unreachable}")
        assert False, f"Unreachable nodes: {unreachable}"

    tl.passed(
        f"OCI provenance complete for {len(sources)} source(s), "
        f"all {len(nodes)} PXE node(s) reachable"
    )
