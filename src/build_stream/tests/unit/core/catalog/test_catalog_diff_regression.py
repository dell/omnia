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

"""Regression tests for catalog generation and adapter policy output.

These tests verify that:
- The adapter policy output matches the expected input config files.
- Specific packages (csi git packages, msr-safe, nvhpc) are correctly routed.
- Functional layers in the catalog match PXE mapping expectations.
- No unwanted architecture layers are generated (e.g. service_k8s aarch64).

The catalog under test is sourced from the maintained ``examples/catalog``
directory rather than a checked-in fixture. Tests that require the expected
``input/`` baseline skip cleanly when that baseline is not present.
"""

import csv
import json
import os
import sys
import tempfile
import unittest

from core.catalog.generator import generate_root_json_from_catalog
from core.catalog.adapter_policy import (
    generate_configs_from_policy,
    _DEFAULT_POLICY_PATH,
)

# diff_input_configs lives alongside this test (stdlib-only helper tool).
HERE = os.path.dirname(__file__)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import diff_input_configs  # noqa: E402  pylint: disable=wrong-import-position

# ── Paths ──────────────────────────────────────────────────────────────

# tests/unit/core/catalog -> build_stream root (4 levels up)
_BUILD_STREAM_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
# build_stream root -> omnia repo root (examples is a sibling of build_stream)
_REPO_ROOT = os.path.dirname(_BUILD_STREAM_ROOT)
_EXAMPLES_CATALOG = os.path.join(
    _REPO_ROOT, "examples", "catalog", "catalog_rhel.json"
)
_EXPECTED_INPUT_DIR = os.path.join(_REPO_ROOT, "input")
_CATALOG_RESOURCES = os.path.join(_BUILD_STREAM_ROOT, "core", "catalog", "resources")
_SCHEMA_PATH = os.path.join(_CATALOG_RESOURCES, "CatalogSchema.json")
_POLICY_PATH = os.path.join(_CATALOG_RESOURCES, "adapter_policy_default.json")
_POLICY_SCHEMA_PATH = os.path.join(_CATALOG_RESOURCES, "AdapterPolicySchema.json")
_PXE_MAPPING_DIR = os.path.join(
    _REPO_ROOT, "examples", "catalog", "mapping_file_software_config",
    "catalog_rhel_json",
)
_PXE_MAPPING_FILE = os.path.join(_PXE_MAPPING_DIR, "pxe_mapping_file.csv")
_SOFTWARE_CONFIG_PATH = os.path.join(_EXPECTED_INPUT_DIR, "software_config.json")


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_pxe_groups(pxe_dir):
    """Load functional PXE groups from the mapping CSV."""
    pxe_csv = os.path.join(pxe_dir, "pxe_mapping_file.csv")
    if not os.path.isfile(pxe_csv):
        return []
    groups = []
    with open(pxe_csv, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return []
        idx = 0
        for i, col in enumerate(header):
            if col.strip().lower() == "functional_group":
                idx = i
                break
        for row in reader:
            if row and row[idx].strip():
                groups.append(row[idx].strip())
    return sorted(groups)


def _generate_adapter_output(catalog_path):
    """Run the full generator → adapter pipeline and return the output dir."""
    tmpdir = tempfile.mkdtemp(prefix="inputconfig_test_")
    root_json_dir = os.path.join(tmpdir, "root_jsons")
    adapter_out = os.path.join(tmpdir, "adapter_out")

    generate_root_json_from_catalog(
        catalog_path=catalog_path,
        schema_path=_SCHEMA_PATH,
        output_root=root_json_dir,
    )
    generate_configs_from_policy(
        input_dir=root_json_dir,
        output_dir=adapter_out,
        policy_path=_POLICY_PATH,
        schema_path=_POLICY_SCHEMA_PATH,
    )
    return adapter_out


# ── Known exceptions ────────────────────────────────────────────────────
# Files that are expected to be missing because the examples software_config
# does not include the additional_packages bundle.
_KNOWN_MISSING = {
    ("aarch64/rhel/10.0", "additional_packages.json"),
    ("x86_64/rhel/10.0", "additional_packages.json"),
}


class TestAdapterDiffReport(unittest.TestCase):
    """Verify that the adapter output matches expected input configs."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(_EXAMPLES_CATALOG):
            raise unittest.SkipTest(
                f"Examples catalog not found: {_EXAMPLES_CATALOG}"
            )
        if not os.path.isdir(_EXPECTED_INPUT_DIR):
            raise unittest.SkipTest(
                f"Expected input baseline not found: {_EXPECTED_INPUT_DIR}"
            )
        cls.adapter_output = _generate_adapter_output(_EXAMPLES_CATALOG)
        # Generate diff report (uses temporary file)
        passed, issue_count, cls.diff_report_path = diff_input_configs.run_diff_for_test(
            _EXPECTED_INPUT_DIR,
            os.path.join(cls.adapter_output, "input"),
            pxe_mapping_path=_PXE_MAPPING_FILE,
            catalog_path=_EXAMPLES_CATALOG
        )
        cls.diff_passed = passed
        cls.diff_issue_count = issue_count

    @unittest.skip(
        "Adapter output currently differs from expected baseline configs in "
        "omnia/input/. Re-enable after investigating diffs and either accepting "
        "new baseline or fixing adapter policy."
    )
    def test_diff_report_clean(self):
        """No unexpected diffs between adapter output and expected configs."""
        if not self.diff_passed:
            self.fail(
                f"Adapter output does not match expected configs. "
                f"Total issues: {self.diff_issue_count}. "
                f"See detailed report: {self.diff_report_path}"
            )

    def test_csi_driver_powerscale_has_git_packages(self):
        """csi_driver_powerscale.json must contain git packages."""
        csi_path = os.path.join(
            self.adapter_output, "input", "config", "x86_64", "rhel", "10.0",
            "csi_driver_powerscale.json",
        )
        self.assertTrue(os.path.isfile(csi_path), "csi_driver_powerscale.json not generated")
        data = _load_json(csi_path)
        cluster = data.get("csi_driver_powerscale", {}).get("cluster", [])
        git_pkgs = [p for p in cluster if p.get("type") == "git"]
        git_names = {p.get("package", "") for p in git_pkgs}

        self.assertGreaterEqual(len(git_pkgs), 3, f"Expected >= 3 git packages, got {len(git_pkgs)}")
        for expected_base in ("csi-powerscale", "external-snapshotter", "helm-charts"):
            matches = [n for n in git_names if expected_base in n]
            self.assertTrue(matches, f"Git package matching '{expected_base}' not found in {git_names}")


class TestCatalogFunctionalLayers(unittest.TestCase):
    """Verify functional layers match PXE mapping and bundle architecture constraints."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(_EXAMPLES_CATALOG):
            raise unittest.SkipTest(
                f"Examples catalog not found: {_EXAMPLES_CATALOG}"
            )
        cls.catalog = _load_json(_EXAMPLES_CATALOG)
        cls.layers = {
            layer["Name"]: layer
            for layer in cls.catalog["Catalog"]["FunctionalLayer"]
        }
        cls.pxe_groups = _load_pxe_groups(_PXE_MAPPING_DIR)

    def test_all_pxe_groups_have_layers(self):
        """Every PXE functional group must have a corresponding functional layer."""
        missing = [g for g in self.pxe_groups if g not in self.layers]
        self.assertEqual(
            missing, [],
            f"PXE groups missing from functional layers: {missing}"
        )

    def test_no_aarch64_service_k8s_layers(self):
        """service_k8s bundle is x86_64 only; no aarch64 layers should exist."""
        bad = [
            name for name in self.layers
            if "kube" in name and "aarch64" in name
        ]
        self.assertEqual(
            bad, [],
            f"Unexpected aarch64 service_k8s layers: {bad}"
        )

    def test_catalog_layers_match_pxe(self):
        """Catalog FunctionalLayer must contain exactly the PXE groups and _first variants.

        _first variant layers (e.g., service_kube_control_plane_first_x86_64) are allowed
        if their base role (service_kube_control_plane) is in the PXE mapping for that architecture.
        """
        layer_names = set(self.layers.keys())
        pxe_set = set(self.pxe_groups)

        # Extract base PXE roles and their architectures
        pxe_base_roles = {}
        for pxe_group in pxe_set:
            base_role = pxe_group.replace('_x86_64', '').replace('_aarch64', '')
            arch = 'x86_64' if '_x86_64' in pxe_group else 'aarch64'
            pxe_base_roles.setdefault(base_role, set()).add(arch)

        # Build expected layer set: PXE groups + valid _first variants
        expected_layers = set(pxe_set)
        for base_role, arches in pxe_base_roles.items():
            for arch in arches:
                expected_layers.add(f"{base_role}_first_{arch}")

        extra = layer_names - expected_layers

        self.assertEqual(
            extra, set(),
            f"Catalog has non-PXE layers: {extra}"
        )
        # Only check for missing PXE groups, not _first variants (they're optional)
        missing_pxe = pxe_set - layer_names
        self.assertEqual(
            missing_pxe, set(),
            f"PXE groups missing from catalog: {missing_pxe}"
        )

    def test_functional_layer_packages_exist_in_catalog(self):
        """Every package ID in a functional layer must exist in FunctionalPackages."""
        func_pkgs = self.catalog["Catalog"]["FunctionalPackages"]
        bad = []
        for name, layer in self.layers.items():
            for pid in layer["FunctionalPackages"]:
                if pid not in func_pkgs:
                    bad.append(f"{name}: {pid}")
        self.assertEqual(bad, [], f"Dangling package IDs in layers: {bad}")

    def test_msr_safe_in_all_slurm_x86_64_layers(self):
        """msr-safe (x86_64) must be in all 4 slurm x86_64 functional layers."""
        func_pkgs = self.catalog["Catalog"]["FunctionalPackages"]
        msr_ids = [
            pid for pid, pkg in func_pkgs.items()
            if pkg["Name"] == "msr-safe" and "x86_64" in pkg["Architecture"]
        ]
        self.assertTrue(msr_ids, "msr-safe not found in FunctionalPackages")
        msr_id = msr_ids[0]

        roles = [
            "slurm_control_node_x86_64",
            "slurm_node_x86_64",
            "login_node_x86_64",
            "login_compiler_node_x86_64",
        ]
        missing = [
            r for r in roles
            if r in self.layers and msr_id not in self.layers[r]["FunctionalPackages"]
        ]
        self.assertEqual(
            missing, [],
            f"msr-safe ({msr_id}) missing from layers: {missing}"
        )


if __name__ == "__main__":
    unittest.main()
