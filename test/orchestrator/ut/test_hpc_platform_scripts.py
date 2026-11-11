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

"""Minimal contracts for per-node RHEL HPC paths."""

from pathlib import Path
import os
import subprocess
import tempfile

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = REPOSITORY_ROOT / "src" / "orchestrator"
SLURM_ROLE = ORCHESTRATOR_ROOT / "roles" / "slurm_config"
PROVISION_HPC = (
    ORCHESTRATOR_ROOT / "roles" / "provision_common" / "templates" / "hpc_tools"
)
HELPER = SLURM_ROLE / "templates" / "omnia_platform.sh.j2"


def _detect(os_version, arch):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        release = root / "os-release"
        release.write_text(f"ID=rhel\nVERSION_ID={os_version}\n", encoding="utf-8")
        env = os.environ.copy()
        env["OMNIA_HPC_TOOLS_DIR"] = str(root / "hpc_tools")
        env["OMNIA_TEST_ARCH"] = arch
        command = (
            f"source {HELPER}; omnia_detect_platform {release}; "
            'printf "%s|%s" "$OMNIA_PLATFORM_ROOT" "$OMNIA_PULP_PLATFORM_PATH"'
        )
        return subprocess.run(
            ["bash", "-c", command],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )


@pytest.mark.parametrize(
    ("version", "arch", "storage", "pulp"),
    [
        ("10.0", "x86_64", "platforms/rhel/10.0/x86_64", "x86_64/rhel/10.0"),
        ("10.2", "x86_64", "platforms/rhel/10.2/x86_64", "x86_64/rhel/10.2"),
        ("10.3", "arm64", "platforms/rhel/10.3/aarch64", "aarch64/rhel/10.3"),
    ],
)
def test_node_platform_selects_storage_and_pulp_paths(version, arch, storage, pulp):
    """ORCH_UT_040: Resolve per-node storage and Pulp platform paths."""
    result = _detect(version, arch)
    assert result.returncode == 0, result.stderr
    platform_root, pulp_path = result.stdout.split("|")
    assert platform_root.endswith(storage)
    assert pulp_path == pulp


def test_os_dependent_scripts_do_not_use_global_cluster_version():
    """ORCH_UT_041: Slurm HPC scripts avoid the global OS version."""
    scripts = (
        SLURM_ROLE / "templates" / "pull_benchmarks.sh.j2",
        PROVISION_HPC / "install_ucx.sh.j2",
        PROVISION_HPC / "install_openmpi.sh.j2",
        PROVISION_HPC / "configure_ucx_openmpi_env.sh.j2",
        PROVISION_HPC / "cuda_lock_manager.sh.j2",
        PROVISION_HPC / "install_cuda_toolkit.sh.j2",
        PROVISION_HPC / "install_cuda_driver.sh.j2",
        PROVISION_HPC / "slurm_cuda_coordinator.sh.j2",
    )
    for script in scripts:
        text = script.read_text(encoding="utf-8")
        assert "omnia_detect_platform" in text
        assert "cluster_os_version" not in text


def test_runtime_templates_are_owned_by_provision_common():
    """ORCH_UT_042: Runtime templates are owned by the provisioning role."""
    template_names = (
        "install_ucx.sh.j2",
        "install_openmpi.sh.j2",
        "configure_ucx_openmpi_env.sh.j2",
        "cuda_lock_manager.sh.j2",
        "install_cuda_toolkit.sh.j2",
        "install_cuda_driver.sh.j2",
        "slurm_cuda_coordinator.sh.j2",
    )
    assert not (ORCHESTRATOR_ROOT / "roles" / "configure_ochami").exists()
    for name in template_names:
        assert (PROVISION_HPC / name).is_file()


def test_custom_mpi_installers_are_not_automatically_run():
    """ORCH_UT_043: Custom MPI installers remain manual and optional."""
    metadata_root = (
        ORCHESTRATOR_ROOT
        / "roles"
        / "provision_common"
        / "templates"
        / "metadata_svc"
    )
    for node_type in ("slurm_node", "login_compiler_node"):
        for arch in ("x86_64", "aarch64"):
            text = (metadata_root / f"ms-group-{node_type}_{arch}.yaml.j2").read_text(
                encoding="utf-8"
            )
            assert "        - /usr/local/bin/install_ucx.sh" not in text
            assert "        - /usr/local/bin/install_openmpi.sh" not in text


def test_benchmark_downloader_is_offline_and_architecture_aware():
    """ORCH_UT_044: Benchmarks use Pulp and node-local platform metadata."""
    script = (SLURM_ROLE / "templates" / "pull_benchmarks.sh.j2").read_text(
        encoding="utf-8"
    )
    resolver = HELPER.read_text(encoding="utf-8")

    assert "PULP_CONTENT_BASE" in script
    assert "omnia_detect_platform" in script
    assert "OMNIA_PULP_PLATFORM_PATH" in script
    assert "OMNIA_PLATFORM_ROOT" in script
    assert '"msr-safe"' in script
    assert 'PULP_CONTENT_BASE="https://${PULP_SERVER}/pulp/content/' in script
    assert "FAILED_COUNT" in script and "exit ${EXIT_CODE:-0}" in script
    assert "https://github.com" not in script
    assert "uname -m" in resolver
    assert "x86_64|amd64" in resolver and "aarch64|arm64" in resolver
