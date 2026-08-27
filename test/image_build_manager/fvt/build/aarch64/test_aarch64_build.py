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
Image Build Build — AArch64-specific Verification.

Verifies aarch64 build infrastructure: SSH connectivity, node preparation,
work directory creation, builder image pull, and regctl installation.
These tests run on the OIM (localhost) and validate the state of the
remote aarch64 node after build_image_aarch64.yml completes.
"""

import pytest

from library.functions import (
    TestLogger,
    load_test_config,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import CMDS, ENV_OMNIA_DATA_PATH


# =============================================================================
# HELPERS
# =============================================================================

def _get_data_path(host) -> str:
    """Read OMNIA_DATA_PATH from the target host environment."""
    result = host.check_output(f"echo ${ENV_OMNIA_DATA_PATH}").strip()
    assert result, (
        f"${ENV_OMNIA_DATA_PATH} is not set on the target host. "
        "Run omnia.sh --setup-venv first."
    )
    return result


def _get_aarch64_ip(host):
    """Read aarch64_inventory_host_ip from image_build_config.yml on target."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    data_path = _get_data_path(host)
    cfg_path = (
        f"{data_path}/image_build_manager/input/{project}"
        f"/image_build_config.yml"
    )
    result = host.run(CMDS["cat_file"].format(path=cfg_path))
    if result.rc != 0:
        return ""
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("aarch64_inventory_host_ip:"):
            val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            return val
    return ""


def _skip_if_no_aarch64(host):
    """Skip test if aarch64 is not configured."""
    ip = _get_aarch64_ip(host)
    if not ip:
        pytest.skip("aarch64_inventory_host_ip not configured — skipping")
    return ip


# =============================================================================
# TESTS
# =============================================================================

@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(10)
def test_aarch64_ssh_connectivity(host):
    """Verify passwordless SSH from OIM to aarch64 node works."""
    tc = TC["aarch64_ssh_connectivity"]
    tl = TestLogger(tc["title"], tc["id"])
    ip = _skip_if_no_aarch64(host)

    result = host.run(
        f"ssh -o BatchMode=yes -o ConnectTimeout=10 "
        f"-o StrictHostKeyChecking=no root@{ip} 'echo OK'"
    )

    if result.rc == 0 and "OK" in result.stdout:
        tl.passed(f"Passwordless SSH to {ip} works")
    else:
        tl.failed(
            f"SSH to {ip} failed (rc={result.rc})",
            result.stderr,
        )

    assert result.rc == 0 and "OK" in result.stdout, (
        f"Passwordless SSH to aarch64 node {ip} failed. "
        f"rc={result.rc}, stderr={result.stderr}"
    )


@pytest.mark.aarch64
@pytest.mark.sanity
@pytest.mark.order(11)
def test_aarch64_work_dirs(host):
    """Verify aarch64 work directories exist on the remote node."""
    tc = TC["aarch64_work_dirs"]
    tl = TestLogger(tc["title"], tc["id"])
    ip = _skip_if_no_aarch64(host)

    # Work dirs on the aarch64 node use a fixed path — the remote node
    # does not run omnia.sh and has no OMNIA_DATA_PATH env var.
    work_dir = "/opt/omnia/image_build_manager"
    dirs = [
        work_dir,
        f"{work_dir}/openchami/aarch64",
        f"{work_dir}/workdir",
        f"{work_dir}/log",
    ]

    missing = []
    for d in dirs:
        result = host.run(
            f"ssh -o BatchMode=yes -o ConnectTimeout=10 "
            f"-o StrictHostKeyChecking=no root@{ip} "
            f"'test -d {d} && echo exists'"
        )
        if "exists" not in result.stdout:
            missing.append(d)

    if not missing:
        tl.passed(f"All {len(dirs)} work directories exist on {ip}")
    else:
        tl.failed(f"{len(missing)} work directories missing on {ip}")

    assert not missing, (
        f"Missing aarch64 work directories on {ip}: {missing}"
    )


@pytest.mark.aarch64
@pytest.mark.functional
@pytest.mark.order(12)
def test_aarch64_builder_image(host):
    """Verify builder container image exists on aarch64 node."""
    tc = TC["aarch64_builder_image"]
    tl = TestLogger(tc["title"], tc["id"])
    ip = _skip_if_no_aarch64(host)

    result = host.run(
        f"ssh -o BatchMode=yes -o ConnectTimeout=10 "
        f"-o StrictHostKeyChecking=no root@{ip} "
        f"'podman images --format \"{{{{.Repository}}}}:{{{{.Tag}}}}\" "
        f"| grep -E \"aarch64-image-(builder|thrillhouse)\"'"
    )

    if result.rc == 0 and result.stdout.strip():
        images = result.stdout.strip().splitlines()
        tl.passed(
            f"Builder image found on {ip}: {images[0]}"
        )
    else:
        tl.failed(f"No aarch64 builder image on {ip}")

    assert result.rc == 0 and result.stdout.strip(), (
        f"aarch64 builder image not found on {ip}. "
        f"Ensure prepare_aarch64_node pulled the image successfully."
    )


@pytest.mark.aarch64
@pytest.mark.functional
@pytest.mark.order(13)
def test_aarch64_regctl_installed(host):
    """Verify regctl binary is installed and functional on aarch64 node."""
    tc = TC["aarch64_regctl_installed"]
    tl = TestLogger(tc["title"], tc["id"])
    ip = _skip_if_no_aarch64(host)

    result = host.run(
        f"ssh -o BatchMode=yes -o ConnectTimeout=10 "
        f"-o StrictHostKeyChecking=no root@{ip} "
        f"'/usr/local/bin/regctl version'"
    )

    if result.rc == 0 and result.stdout.strip():
        tl.passed(f"regctl on {ip}: {result.stdout.strip()}")
    else:
        tl.failed(f"regctl not functional on {ip}")

    assert result.rc == 0, (
        f"regctl not installed or not functional on aarch64 node {ip}. "
        f"rc={result.rc}, stderr={result.stderr}"
    )


@pytest.mark.aarch64
@pytest.mark.functional
@pytest.mark.order(14)
def test_aarch64_architecture(host):
    """Verify the aarch64 node is actually running ARM architecture."""
    tc = TC["aarch64_architecture"]
    tl = TestLogger(tc["title"], tc["id"])
    ip = _skip_if_no_aarch64(host)

    result = host.run(
        f"ssh -o BatchMode=yes -o ConnectTimeout=10 "
        f"-o StrictHostKeyChecking=no root@{ip} 'uname -m'"
    )

    arch = result.stdout.strip()
    if result.rc == 0 and arch == "aarch64":
        tl.passed(f"Node {ip} architecture: {arch}")
    else:
        tl.failed(f"Node {ip} architecture: {arch} (expected aarch64)")

    assert result.rc == 0 and arch == "aarch64", (
        f"aarch64 node {ip} reports architecture '{arch}', expected 'aarch64'"
    )
