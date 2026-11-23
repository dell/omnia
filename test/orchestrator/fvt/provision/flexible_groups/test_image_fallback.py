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
Tests for Image Build Manager Flexible Group Fallback Contract Compatibility.

Test Cases:
- TC_FVT_image_005: Verify Image Build Manager fallback contracts preserve valid
  fg_ identity and complete architecture-specific kernel, initrd, and rootfs artifacts.
- TC_FVT_standard_regression_014: Verify standard functional group fallback contracts
  remain compatible and coexist with flexible groups without regression.
"""

# pylint: disable=wrong-import-position,redefined-outer-name

import sys
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[5]
SOURCE_PLUGIN_ROOT = REPO_ROOT / "src" / "orchestrator" / "plugins"
if str(SOURCE_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_PLUGIN_ROOT))

from module_utils.image_fallback_resolver import (  # noqa: E402
    extract_architecture_entries,
    resolve_boot_image_fallback,
)
FIXTURES_DIR = (
    REPO_ROOT / "test" / "fixtures" / "build_status" / "flexible_groups"
)


def _load_status_fixture(filename: str) -> dict:
    path = FIXTURES_DIR / filename
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def valid_build_status():
    """Load valid build_status fixture containing flexible and standard groups."""
    return _load_status_fixture("valid_flexible_build_status.yml")


@pytest.mark.fvt
@pytest.mark.order(40005)
class TestFlexibleGroupImageFallback:
    """TC_FVT_image_005: Verify flexible functional group fallback contracts."""

    @pytest.mark.parametrize(
        ("fg_name", "arch"),
        [
            ("fg_webserver_rhel_10_0_x86_64", "x86_64"),
            ("fg_database_rhel_10_2_x86_64", "x86_64"),
            ("fg_ai_worker_rhel_10_2_aarch64", "aarch64"),
        ],
    )
    def test_publish_complete_flexible_group_artifacts(
        self, valid_build_status, fg_name, arch
    ):
        """FR-3.1: Valid fg_ layers preserve full identity and complete artifacts."""
        usable, artifacts, error = resolve_boot_image_fallback(
            valid_build_status, fg_name, arch
        )
        assert usable is True, f"Failed resolving fallback for {fg_name}: {error}"
        assert error == ""

        # Verify kernel, initrd, and rootfs are present and complete
        assert "kernel" in artifacts and len(artifacts["kernel"]) > 0
        assert "initrd" in artifacts and len(artifacts["initrd"]) > 0
        assert "rootfs" in artifacts and len(artifacts["rootfs"]) > 0
        assert "endpoint" in artifacts and artifacts["endpoint"].startswith("http")

        # Verify artifact paths match full identity and architecture
        assert fg_name in artifacts["kernel"]
        assert fg_name in artifacts["initrd"]
        assert fg_name in artifacts["rootfs"]

    def test_architecture_extraction_isolation(self, valid_build_status):
        """FR-3.1: Architecture blocks isolate x86_64 and aarch64 image entries."""
        x86_entries = extract_architecture_entries(valid_build_status, "x86_64")
        x86_fgs = [e["functional_group"] for e in x86_entries]
        assert "fg_webserver_rhel_10_0_x86_64" in x86_fgs
        assert "fg_ai_worker_rhel_10_2_aarch64" not in x86_fgs

        arm_entries = extract_architecture_entries(valid_build_status, "aarch64")
        arm_fgs = [e["functional_group"] for e in arm_entries]
        assert "fg_ai_worker_rhel_10_2_aarch64" in arm_fgs
        assert "fg_webserver_rhel_10_0_x86_64" not in arm_fgs

    @pytest.mark.parametrize(
        ("fixture_file", "expected_error_phrase"),
        [
            ("missing_kernel_build_status.yml", "missing or empty 'kernel'"),
            ("missing_initrd_build_status.yml", "missing or empty 'initrd'"),
            ("missing_rootfs_build_status.yml", "missing or empty 'image' (rootfs)"),
            ("stale_failed_build_status.yml", "overall_status='failed'"),
            (
                "arch_mismatch_build_status.yml",
                "No image entries found for architecture 'x86_64'",
            ),
            ("ambiguous_build_status.yml", "Ambiguous fallback metadata"),
        ],
    )
    def test_reject_unusable_fallback_metadata(
        self, fixture_file, expected_error_phrase
    ):
        """FR-3.1: Unusable fallback metadata fails safely before mutation."""
        status_data = _load_status_fixture(fixture_file)
        usable, artifacts, error = resolve_boot_image_fallback(
            status_data, "fg_webserver_rhel_10_0_x86_64", "x86_64"
        )
        assert usable is False
        assert artifacts == {}
        assert expected_error_phrase.lower() in error.lower()


@pytest.mark.fvt
@pytest.mark.order(40014)
class TestStandardGroupContractRegression:
    """TC_FVT_standard_regression_014: Verify standard functional group fallback regression."""

    @pytest.mark.parametrize(
        ("fg_name", "arch"),
        [
            ("slurm_control_node_rhel_10_0_x86_64", "x86_64"),
            ("service_kube_control_plane_rhel_10_0_x86_64", "x86_64"),
            ("os_rhel_10_2_x86_64", "x86_64"),
            ("slurm_node_rhel_10_0_aarch64", "aarch64"),
        ],
    )
    def test_standard_groups_preserve_fallback_contracts(
        self, valid_build_status, fg_name, arch
    ):
        """AC-008: Standard functional groups retain complete kernel, initrd, and rootfs."""
        usable, artifacts, error = resolve_boot_image_fallback(
            valid_build_status, fg_name, arch
        )
        assert usable is True, f"Standard group fallback resolution failed: {error}"
        assert error == ""
        assert len(artifacts["kernel"]) > 0
        assert len(artifacts["initrd"]) > 0
        assert len(artifacts["rootfs"]) > 0
        assert fg_name in artifacts["kernel"]

    def test_coexistence_without_interference(self, valid_build_status):
        """AC-008: Standard and flexible groups coexist in same manifest without conflict."""
        x86_entries = extract_architecture_entries(valid_build_status, "x86_64")
        all_fgs = {e["functional_group"] for e in x86_entries}

        # Check standard groups present
        assert "slurm_control_node_rhel_10_0_x86_64" in all_fgs
        assert "service_kube_control_plane_rhel_10_0_x86_64" in all_fgs
        assert "os_rhel_10_2_x86_64" in all_fgs

        # Check flexible groups present
        assert "fg_webserver_rhel_10_0_x86_64" in all_fgs
        assert "fg_database_rhel_10_2_x86_64" in all_fgs

        # Total entries in x86_64 block is exactly 5
        assert len(x86_entries) == 5
