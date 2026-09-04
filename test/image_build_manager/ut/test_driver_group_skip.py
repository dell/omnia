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
"""Tests for driver_group skip logic in parse_catalog.py.

Driver groups (GPU, InfiniBand, storage drivers) must be excluded from
image builds because they are installed post-boot via provisioning,
not baked into the OS image.
"""

import json
import pathlib
import sys
import types

import pytest


# ut/test_driver... -> ut/ -> image_build_manager/ -> test/ -> omnia-bsm/
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

SAMPLE_CATALOG = (
    REPO_ROOT / "src" / "main" / "samples"
    / "catalog_rhel_10_0_x86_aarch64.json"
)

# ---------------------------------------------------------------------------
# Mock ansible imports so parse_catalog.py can be imported outside Ansible
# ---------------------------------------------------------------------------
if "ansible" not in sys.modules:
    _ansible = types.ModuleType("ansible")
    _ansible_mu = types.ModuleType("ansible.module_utils")
    _ansible_mu_basic = types.ModuleType("ansible.module_utils.basic")

    class _FakeAnsibleModule:  # noqa: D101 — minimal stub
        pass

    _ansible_mu_basic.AnsibleModule = _FakeAnsibleModule
    _ansible.module_utils = _ansible_mu
    sys.modules["ansible"] = _ansible
    sys.modules["ansible.module_utils"] = _ansible_mu
    sys.modules["ansible.module_utils.basic"] = _ansible_mu_basic

# Add parse_catalog module to path
_PLUGINS_DIR = (
    REPO_ROOT / "src" / "image_build_manager" / "plugins" / "modules"
)
if str(_PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGINS_DIR))

# Import helper functions directly (not the Ansible module entry point)
from parse_catalog import (  # noqa: E402
    _is_driver_group,
    _collect_driver_groups,
    resolve_catalog,
    DRIVER_GROUP_MARKER,
)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def minimal_catalog_with_drivers(tmp_path):
    """Create a minimal catalog JSON with driver groups for testing."""
    catalog = {
        "catalog": {
            "name": "test-catalog",
            "version": "1.0",
            "identifier": "test-driver-skip",
            "functionallayer": [
                {
                    "name": "compute_node_rhel_10_0_x86_64",
                    "components": [
                        "baseos_group_10.0",
                        "slurm_group",
                        "nvidia_stack_driver_groupv1",
                    ],
                },
                {
                    "name": "slurm_node_rhel_10_0_x86_64",
                    "components": [
                        "baseos_group_10.0",
                        "slurm_group",
                    ],
                },
            ],
            "groups": {
                "baseos_group_10.0": {
                    "name": "baseos_group_10.0",
                    "type": "base_os",
                    "os_version": "10.0",
                    "os": "rhel",
                    "components": ["kernel", "systemd"],
                },
                "slurm_group": {
                    "name": "slurm_group",
                    "type": "group",
                    "components": ["munge", "slurm_slurmd"],
                },
            },
            # Driver groups at catalog top level (not in groups)
            "nvidia_stack_driver_groupv1": {
                "name": "nvidia_stack_v1",
                "type": "group",
                "description": "GPU drivers",
                "components": ["nvidia_driver", "cuda_toolkit"],
            },
            "infiniband_stack_driver_groupv1": {
                "name": "infiniband_stack_v1",
                "type": "group",
                "description": "InfiniBand stack",
                "components": ["doca_ofed"],
            },
            "packages": {
                "kernel": {
                    "name": "kernel",
                    "packagetype": "rpm",
                    "sources": [{"architecture": "x86_64", "reponame": "baseos"}],
                },
                "systemd": {
                    "name": "systemd",
                    "packagetype": "rpm",
                    "sources": [{"architecture": "x86_64", "reponame": "baseos"}],
                },
                "munge": {
                    "name": "munge",
                    "packagetype": "rpm",
                    "sources": [{"architecture": "x86_64", "reponame": "baseos"}],
                },
                "slurm_slurmd": {
                    "name": "slurm-slurmd",
                    "packagetype": "rpm",
                    "sources": [{"architecture": "x86_64", "reponame": "baseos"}],
                },
                "nvidia_driver": {
                    "name": "nvidia-driver",
                    "packagetype": "rpm",
                    "sources": [{"architecture": "x86_64", "reponame": "nvidia"}],
                },
                "cuda_toolkit": {
                    "name": "cuda-toolkit",
                    "packagetype": "rpm",
                    "sources": [{"architecture": "x86_64", "reponame": "nvidia"}],
                },
                "doca_ofed": {
                    "name": "doca-ofed",
                    "packagetype": "rpm",
                    "sources": [{"architecture": "x86_64", "reponame": "mlnx"}],
                },
            },
        }
    }
    catalog_file = tmp_path / "catalog_driver_test.json"
    catalog_file.write_text(json.dumps(catalog), encoding="utf-8")
    return str(catalog_file)


# ── _is_driver_group tests ──────────────────────────────────────────────


class TestIsDriverGroup:
    """Test the _is_driver_group helper function."""

    def test_nvidia_driver_group(self):
        assert _is_driver_group("nvidia_stack_driver_groupv1") is True

    def test_infiniband_driver_group(self):
        assert _is_driver_group("infiniband_stack_driver_groupv1") is True

    def test_vast_driver_group(self):
        assert _is_driver_group("vast_stack_driver_groupv1") is True

    def test_regular_group_not_driver(self):
        assert _is_driver_group("slurm_group") is False

    def test_baseos_not_driver(self):
        assert _is_driver_group("baseos_group_10.0") is False

    def test_empty_string(self):
        assert _is_driver_group("") is False

    def test_driver_group_substring_anywhere(self):
        """Any key containing driver_group should be detected."""
        assert _is_driver_group("custom_driver_group_v2") is True

    def test_partial_match_no_false_positive(self):
        """'driver' alone should not match — must contain 'driver_group'."""
        assert _is_driver_group("nvidia_driver") is False
        assert _is_driver_group("driver_packages") is False


# ── _collect_driver_groups tests ────────────────────────────────────────


class TestCollectDriverGroups:
    """Test _collect_driver_groups top-level detection."""

    def test_finds_driver_groups_at_top_level(self):
        catalog = {
            "name": "test",
            "version": "1.0",
            "identifier": "test",
            "functionallayer": [],
            "groups": {},
            "packages": {},
            "nvidia_stack_driver_groupv1": {"name": "nvidia"},
            "infiniband_stack_driver_groupv1": {"name": "ib"},
            "vast_stack_driver_groupv1": {"name": "vast"},
        }
        result = _collect_driver_groups(catalog)
        assert result == [
            "infiniband_stack_driver_groupv1",
            "nvidia_stack_driver_groupv1",
            "vast_stack_driver_groupv1",
        ]

    def test_no_driver_groups(self):
        catalog = {
            "name": "test",
            "functionallayer": [],
            "groups": {},
            "packages": {},
        }
        assert _collect_driver_groups(catalog) == []

    def test_does_not_include_standard_keys(self):
        """Standard keys (name, groups, etc.) must not be returned."""
        catalog = {
            "name": "test",
            "version": "1.0",
            "identifier": "x",
            "description": "y",
            "functionallayer": [],
            "groups": {},
            "packages": {},
        }
        assert _collect_driver_groups(catalog) == []


# ── resolve_catalog driver skip tests ───────────────────────────────────


class TestResolveCatalogDriverSkip:
    """Test that resolve_catalog excludes driver groups from build output."""

    def test_driver_components_excluded_from_compute_packages(
        self, minimal_catalog_with_drivers
    ):
        """Packages from driver_group components must not appear in compute_images_dict."""
        result = resolve_catalog(
            catalog_file=minimal_catalog_with_drivers,
            build_arch="x86_64",
        )
        for fg_name, fg_data in result["compute_images_dict"].items():
            pkgs = fg_data["packages"]
            assert "nvidia-driver" not in pkgs, (
                f"Driver package 'nvidia-driver' leaked into {fg_name}"
            )
            assert "cuda-toolkit" not in pkgs, (
                f"Driver package 'cuda-toolkit' leaked into {fg_name}"
            )

    def test_non_driver_packages_still_present(
        self, minimal_catalog_with_drivers
    ):
        """Normal compute packages (munge, slurm) must still be resolved."""
        result = resolve_catalog(
            catalog_file=minimal_catalog_with_drivers,
            build_arch="x86_64",
        )
        compute = result["compute_images_dict"]
        assert len(compute) > 0, "No compute groups resolved"
        # At least one group should have non-driver packages
        all_pkgs = []
        for fg_data in compute.values():
            all_pkgs.extend(fg_data["packages"])
        assert "munge" in all_pkgs, "Non-driver package 'munge' missing"
        assert "slurm-slurmd" in all_pkgs, "Non-driver package 'slurm-slurmd' missing"

    def test_skipped_driver_groups_reported(
        self, minimal_catalog_with_drivers
    ):
        """resolve_catalog must return the list of skipped driver groups."""
        result = resolve_catalog(
            catalog_file=minimal_catalog_with_drivers,
            build_arch="x86_64",
        )
        skipped = result["skipped_driver_groups"]
        assert "nvidia_stack_driver_groupv1" in skipped
        assert "infiniband_stack_driver_groupv1" in skipped

    def test_base_packages_unaffected_by_driver_skip(
        self, minimal_catalog_with_drivers
    ):
        """Base OS packages must not be affected by driver skip logic."""
        result = resolve_catalog(
            catalog_file=minimal_catalog_with_drivers,
            build_arch="x86_64",
        )
        base = result["base_image_packages"]
        assert "kernel" in base
        assert "systemd" in base


# ── Sample catalog validation ───────────────────────────────────────────


class TestSampleCatalogDriverGroups:
    """Validate driver groups in the actual sample catalog."""

    def test_sample_catalog_has_driver_groups(self):
        """Sample catalog must contain at least one driver_group."""
        with open(SAMPLE_CATALOG, "r", encoding="utf-8") as f:
            catalog = json.load(f)["catalog"]
        driver_keys = [
            key for key in catalog.get("groups", {})
            if DRIVER_GROUP_MARKER in key
        ]
        assert len(driver_keys) > 0, (
            "Sample catalog has no driver_group keys. Expected at least "
            "nvidia_stack_driver_groupv1, infiniband_stack_driver_groupv1, "
            "vast_stack_driver_groupv1"
        )

    def test_sample_driver_groups_defined_in_groups(self):
        """Expected driver stacks must be defined in catalog groups."""
        with open(SAMPLE_CATALOG, "r", encoding="utf-8") as f:
            catalog = json.load(f)["catalog"]
        groups = catalog.get("groups", {})
        driver_groups = {
            key for key in groups
            if DRIVER_GROUP_MARKER in key
        }
        expected = {
            "nvidia_stack_driver_groupv1",
            "infiniband_stack_driver_groupv1",
            "vast_stack_driver_groupv1",
        }
        assert expected <= driver_groups, (
            "Sample catalog is missing driver groups: "
            f"{sorted(expected - driver_groups)}"
        )

    def test_sample_driver_groups_excluded_from_resolution(self):
        """Resolving the sample catalog must skip driver groups."""
        with open(SAMPLE_CATALOG, "r", encoding="utf-8") as f:
            catalog = json.load(f)["catalog"]
        expected = {
            component
            for layer in catalog["functionallayer"]
            if layer["name"].endswith("_x86_64")
            for component in layer["components"]
            if DRIVER_GROUP_MARKER in component
        }
        result = resolve_catalog(
            catalog_file=str(SAMPLE_CATALOG),
            build_arch="x86_64",
        )
        assert set(result["skipped_driver_groups"]) == expected

        # Verify no driver packages in compute dict
        for fg_name, fg_data in result["compute_images_dict"].items():
            for pkg in fg_data["packages"]:
                assert "nvidia-driver" not in pkg.lower() or "driver_group" not in fg_name, (
                    f"Driver package '{pkg}' leaked into compute group {fg_name}"
                )
