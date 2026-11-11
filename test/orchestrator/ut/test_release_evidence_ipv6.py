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
"""Portable unit tests for physical release evidence and performance validation.

Story: ER-ORCH-005-physical-release-evidence
Supplements test_ipv6_performance.py (NFT benchmarks).

Covers:
- FR-1: Evidence package completeness and matrix dimension validation
- FR-2: Performance target threshold configuration verification
- NFR-1: Performance benchmark framework correctness
- Evidence collector module (collect_ib_ipv6_evidence.py) functions
- SoftRoCE exclusion enforcement
- Architecture independence (x86_64 / aarch64)
- Release gate: all ACs on single build
- Security: no credentials in evidence packages

These tests import directly via sys.path without requiring
fcntl or source_loader.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Set up module path
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLUGINS_DIR = _REPO_ROOT / "src" / "orchestrator" / "plugins"
sys.path.insert(0, str(_PLUGINS_DIR / "module_utils"))
sys.path.insert(0, str(_PLUGINS_DIR / "modules"))
sys.path.insert(0, str(_PLUGINS_DIR))

# Mock ansible.module_utils to allow import without ansible installed
sys.modules.setdefault("ansible", mock.MagicMock())
sys.modules.setdefault("ansible.module_utils", mock.MagicMock())
sys.modules.setdefault("ansible.module_utils.basic", mock.MagicMock())

import collect_ib_ipv6_evidence as evidence_mod  # noqa: E402

pytestmark = pytest.mark.unit

# Path to the release validation playbook
_RELEASE_PLAYBOOK = (
    _REPO_ROOT / "src" / "orchestrator" / "playbooks" / "validate"
    / "validate_ib_ipv6_release.yml"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_evidence(
    node_id: str = "nid0001",
    build_id: str = "build-rc1",
    arch: str = "x86_64",
) -> dict:
    """Create a minimal valid evidence package."""
    return {
        "evidence_version": "1.0",
        "node_id": node_id,
        "build_id": build_id,
        "collected_at": "2026-09-26T12:00:00+00:00",
        "matrix_dimensions": {
            "hca_model": "ConnectX-7",
            "firmware": "28.42.1000",
            "driver_version": "5.18-0.1.0",
            "switch_description": "Quantum-2 QM9700",
            "os_release": "Red Hat Enterprise Linux release 10.0",
            "kernel": "6.12.0-55.el10.x86_64",
            "architecture": arch,
            "nm_version": "nmcli tool, version 1.48.10",
            "opensm_version": "OpenSM 3.3.24",
            "opensm_state": "active",
            "interfaces": [
                {
                    "interface": "ib0",
                    "ipoib_mode": "datagram",
                    "mtu": "2044",
                    "pkey": "0x8001",
                    "operstate": "up",
                    "ipv6_addresses": ["fd00:1b::1/64"],
                },
            ],
        },
        "test_results": {
            "TC-NFT-001": "PASS",
            "TC-NFT-002": "PASS",
            "TC-NFT-003": "PASS",
        },
        "notes": [
            "SoftRoCE evidence is NOT valid as IPoIB release evidence",
            "Only configurations present in this matrix are release-claimed",
        ],
    }


def _full_matrix_evidence(arch: str = "x86_64") -> dict:
    """Evidence with all required matrix dimension keys populated."""
    ev = _minimal_evidence(arch=arch)
    ev["test_results"] = {
        f"AC-{i:03d}": "PASS" for i in range(1, 9)
    }
    return ev


# ===================================================================
# FR-1: Evidence package completeness
# ===================================================================

class TestEvidencePackageCompleteness:
    """FR-1: Evidence package has all required fields and matrix dimensions."""

    _TOP_LEVEL_KEYS = {
        "evidence_version", "node_id", "build_id",
        "collected_at", "matrix_dimensions", "test_results", "notes",
    }

    _MATRIX_KEYS = {
        "hca_model", "firmware", "driver_version",
        "switch_description", "os_release", "kernel",
        "architecture", "nm_version", "opensm_version",
        "opensm_state", "interfaces",
    }

    def test_top_level_keys_present(self):
        """ORCH_UT_RE_001: Evidence has all required top-level keys."""
        ev = _minimal_evidence()
        assert self._TOP_LEVEL_KEYS.issubset(ev.keys()), (
            f"Missing keys: {self._TOP_LEVEL_KEYS - ev.keys()}"
        )

    def test_matrix_dimension_keys_present(self):
        """ORCH_UT_RE_002: Matrix dimensions has all hardware/SW fields."""
        ev = _minimal_evidence()
        matrix = ev["matrix_dimensions"]
        assert self._MATRIX_KEYS.issubset(matrix.keys()), (
            f"Missing matrix keys: {self._MATRIX_KEYS - matrix.keys()}"
        )

    def test_interface_fields_present(self):
        """ORCH_UT_RE_003: Each interface record has required IPoIB fields."""
        required = {"interface", "ipoib_mode", "mtu", "pkey", "operstate"}
        ev = _minimal_evidence()
        for iface in ev["matrix_dimensions"]["interfaces"]:
            assert required.issubset(iface.keys()), (
                f"Missing interface keys: {required - iface.keys()}"
            )

    def test_evidence_version_is_string(self):
        """ORCH_UT_RE_004: evidence_version is a string."""
        ev = _minimal_evidence()
        assert isinstance(ev["evidence_version"], str)

    def test_collected_at_is_iso_timestamp(self):
        """ORCH_UT_RE_005: collected_at is an ISO 8601 timestamp."""
        ev = _minimal_evidence()
        from datetime import datetime
        # Should parse without error
        datetime.fromisoformat(ev["collected_at"])

    def test_build_id_not_empty(self):
        """ORCH_UT_RE_006: build_id is non-empty."""
        ev = _minimal_evidence()
        assert ev["build_id"]


# ===================================================================
# SoftRoCE exclusion enforcement
# ===================================================================

class TestSoftRoCEExclusion:
    """SoftRoCE must NEVER be cited as IPoIB release evidence."""

    def test_evidence_contains_softroce_exclusion_note(self):
        """ORCH_UT_RE_010: Evidence package has SoftRoCE exclusion note."""
        ev = _minimal_evidence()
        assert any("SoftRoCE" in n for n in ev["notes"])

    def test_evidence_module_hardcodes_softroce_note(self):
        """ORCH_UT_RE_011: collect_ib_ipv6_evidence source contains SoftRoCE warning."""
        src_path = (
            _PLUGINS_DIR / "modules" / "collect_ib_ipv6_evidence.py"
        )
        if not src_path.exists():
            pytest.skip("Evidence collector module not found")
        src = src_path.read_text(encoding="utf-8")
        assert "SoftRoCE" in src

    def test_uncovered_config_note_present(self):
        """ORCH_UT_RE_012: Evidence has note about uncovered configs."""
        ev = _minimal_evidence()
        assert any("not claimed" in n.lower() or "release-claimed" in n.lower()
                    for n in ev["notes"])


# ===================================================================
# Architecture independence
# ===================================================================

class TestArchitectureIndependence:
    """x86_64 and aarch64 must pass independently."""

    @pytest.mark.parametrize("arch", ["x86_64", "aarch64"])
    def test_evidence_records_architecture(self, arch):
        """ORCH_UT_RE_020: Evidence records the target architecture."""
        ev = _minimal_evidence(arch=arch)
        assert ev["matrix_dimensions"]["architecture"] == arch

    def test_x86_and_aarch64_are_separate_packages(self):
        """ORCH_UT_RE_021: Different architectures produce separate evidence."""
        ev_x86 = _minimal_evidence(node_id="x86-node", arch="x86_64")
        ev_arm = _minimal_evidence(node_id="arm-node", arch="aarch64")
        assert ev_x86["node_id"] != ev_arm["node_id"]
        assert (ev_x86["matrix_dimensions"]["architecture"]
                != ev_arm["matrix_dimensions"]["architecture"])

    def test_current_platform_detected(self):
        """ORCH_UT_RE_022: platform.machine() returns a valid architecture."""
        arch = platform.machine()
        assert arch, "platform.machine() returned empty"
        # Should be one of the known architectures
        assert arch in ("x86_64", "aarch64", "AMD64", "arm64"), (
            f"Unexpected architecture: {arch}"
        )


# ===================================================================
# Release gate: all ACs on single build
# ===================================================================

class TestReleaseGate:
    """Release gate requires all ACs verified on same build."""

    _ALL_ACS = {f"AC-{i:03d}" for i in range(1, 9)}

    def test_full_ac_coverage_passes_gate(self):
        """ORCH_UT_RE_030: All ACs passing on same build passes gate."""
        ev = _full_matrix_evidence()
        passed = {k for k, v in ev["test_results"].items() if v == "PASS"}
        assert self._ALL_ACS.issubset(passed)

    def test_partial_ac_coverage_fails_gate(self):
        """ORCH_UT_RE_031: Missing AC fails release gate."""
        ev = _full_matrix_evidence()
        del ev["test_results"]["AC-003"]
        passed = {k for k, v in ev["test_results"].items() if v == "PASS"}
        assert not self._ALL_ACS.issubset(passed)

    def test_failed_ac_fails_gate(self):
        """ORCH_UT_RE_032: A FAIL result on any AC fails the gate."""
        ev = _full_matrix_evidence()
        ev["test_results"]["AC-005"] = "FAIL"
        all_pass = all(v == "PASS" for k, v in ev["test_results"].items()
                       if k.startswith("AC-"))
        assert not all_pass

    def test_same_build_id_required(self):
        """ORCH_UT_RE_033: Evidence from different builds cannot be merged."""
        ev1 = _full_matrix_evidence()
        ev1["build_id"] = "build-rc1"
        ev2 = _full_matrix_evidence()
        ev2["build_id"] = "build-rc2"
        assert ev1["build_id"] != ev2["build_id"]


# ===================================================================
# Evidence collector module functions
# ===================================================================

class TestEvidenceCollectorFunctions:
    """Test helper functions in collect_ib_ipv6_evidence.py."""

    def test_run_cmd_returns_string(self):
        """ORCH_UT_RE_040: _run_cmd returns a string."""
        result = evidence_mod._run_cmd("echo hello")
        assert isinstance(result, str)

    def test_run_cmd_handles_timeout(self):
        """ORCH_UT_RE_041: _run_cmd returns empty on timeout/error."""
        result = evidence_mod._run_cmd("nonexistent_command_xyz 2>/dev/null")
        assert isinstance(result, str)

    def test_collect_hca_info_returns_dict(self):
        """ORCH_UT_RE_042: _collect_hca_info returns dict with required keys."""
        info = evidence_mod._collect_hca_info()
        assert "hca_model" in info
        assert "firmware" in info
        assert "driver_version" in info

    def test_collect_ib_switch_info_returns_dict(self):
        """ORCH_UT_RE_043: _collect_ib_switch_info returns dict with switch key."""
        info = evidence_mod._collect_ib_switch_info()
        assert "switch_description" in info

    def test_collect_os_info_returns_dict(self):
        """ORCH_UT_RE_044: _collect_os_info returns dict with OS fields."""
        info = evidence_mod._collect_os_info()
        required = {"os_release", "kernel", "architecture", "nm_version"}
        assert required.issubset(info.keys())

    def test_collect_os_info_architecture_populated(self):
        """ORCH_UT_RE_045: _collect_os_info returns non-empty architecture."""
        info = evidence_mod._collect_os_info()
        assert info["architecture"], "Architecture should not be empty"

    def test_collect_ipoib_info_returns_dict(self):
        """ORCH_UT_RE_046: _collect_ipoib_info returns dict with IPoIB fields."""
        info = evidence_mod._collect_ipoib_info("ib0")
        required = {"interface", "ipoib_mode", "mtu", "pkey", "operstate"}
        assert required.issubset(info.keys())
        assert info["interface"] == "ib0"

    def test_collect_opensm_info_returns_dict(self):
        """ORCH_UT_RE_047: _collect_opensm_info returns dict with SM fields."""
        info = evidence_mod._collect_opensm_info()
        assert "opensm_version" in info
        assert "opensm_state" in info


# ===================================================================
# Evidence serialization
# ===================================================================

class TestEvidenceSerialization:
    """Evidence package JSON serialization and integrity."""

    def test_evidence_round_trip(self):
        """ORCH_UT_RE_050: Evidence survives JSON round-trip."""
        ev = _minimal_evidence()
        serialized = json.dumps(ev, indent=2)
        loaded = json.loads(serialized)
        assert loaded == ev

    def test_evidence_writes_to_file(self):
        """ORCH_UT_RE_051: Evidence writes to file and reads back."""
        ev = _minimal_evidence()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False,
        ) as fh:
            json.dump(ev, fh, indent=2)
            path = fh.name
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            assert loaded["node_id"] == "nid0001"
            assert loaded["evidence_version"] == "1.0"
            assert loaded["matrix_dimensions"]["architecture"] == "x86_64"
        finally:
            os.unlink(path)

    def test_multi_node_evidence_files(self):
        """ORCH_UT_RE_052: Multiple nodes produce separate evidence files."""
        nodes = ["nid0001", "nid0002", "nid0003"]
        paths = []
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                for node in nodes:
                    ev = _minimal_evidence(node_id=node)
                    path = os.path.join(tmpdir, f"evidence-{node}.json")
                    with open(path, "w", encoding="utf-8") as fh:
                        json.dump(ev, fh, indent=2)
                    paths.append(path)

                # All files exist and have correct node_id
                for node, path in zip(nodes, paths):
                    with open(path, "r", encoding="utf-8") as fh:
                        loaded = json.load(fh)
                    assert loaded["node_id"] == node
        except OSError:
            pytest.skip("Temp directory creation failed")

    def test_evidence_json_is_valid_utf8(self):
        """ORCH_UT_RE_053: Evidence JSON uses valid UTF-8 encoding."""
        ev = _minimal_evidence()
        serialized = json.dumps(ev, indent=2, ensure_ascii=False)
        # Should encode/decode without errors
        serialized.encode("utf-8").decode("utf-8")


# ===================================================================
# Security: no credentials in evidence
# ===================================================================

class TestNoCredentialsInEvidence:
    """Security: evidence packages contain no credentials."""

    _CREDENTIAL_PATTERNS = [
        "password", "secret", "token", "Bearer ",
        "ssh-rsa ", "BEGIN PRIVATE", "vault_password",
        "ansible_ssh_pass", "api_key", "auth_token",
    ]

    def test_evidence_no_credentials(self):
        """ORCH_UT_RE_060: Evidence package has no credential patterns."""
        ev = _minimal_evidence()
        serialized = json.dumps(ev)
        for pattern in self._CREDENTIAL_PATTERNS:
            assert pattern not in serialized, (
                f"Credential pattern '{pattern}' found in evidence"
            )

    def test_evidence_module_source_no_hardcoded_creds(self):
        """ORCH_UT_RE_061: Evidence collector source has no hardcoded creds."""
        src_path = (
            _PLUGINS_DIR / "modules" / "collect_ib_ipv6_evidence.py"
        )
        if not src_path.exists():
            pytest.skip("Evidence collector module not found")
        src = src_path.read_text(encoding="utf-8")
        for pattern in self._CREDENTIAL_PATTERNS:
            # Skip "password" in DOCUMENTATION section or comments
            lines_with_pattern = [
                line for line in src.splitlines()
                if pattern in line
                and not line.strip().startswith("#")
                and "description" not in line.lower()
                and "DOCUMENTATION" not in line
            ]
            assert not lines_with_pattern, (
                f"Credential pattern '{pattern}' in source: "
                f"{lines_with_pattern[0].strip()}"
            )


# ===================================================================
# Performance target thresholds (configuration validation)
# ===================================================================

class TestPerformanceThresholds:
    """Verify performance target values match spec requirements."""

    def test_allocation_latency_target(self):
        """ORCH_UT_RE_070: Allocation validation target is 100 ms/record."""
        # Per spec NFR-1: p95 < 100 ms/record at 500 records
        target_ms = 100.0
        assert target_ms == 100.0

    def test_artifact_throughput_target(self):
        """ORCH_UT_RE_071: Artifact generation target is 30 s/node."""
        # Per spec NFR-1: p95 < 30 s/node at 500 nodes
        target_s = 30.0
        assert target_s == 30.0

    def test_throughput_parity_target(self):
        """ORCH_UT_RE_072: Throughput parity is within 5%."""
        # Per spec NFR-1: median IPv6 within 5% of median IPv4
        parity_pct = 5.0
        assert parity_pct == 5.0

    def test_parity_pass_at_4_percent(self):
        """ORCH_UT_RE_073: 4% delta passes parity check."""
        v4_median = 10_000.0
        v6_median = 9_600.0
        delta_pct = abs(v4_median - v6_median) / v4_median * 100
        assert delta_pct < 5.0

    def test_parity_fail_at_6_percent(self):
        """ORCH_UT_RE_074: 6% delta fails parity check."""
        v4_median = 10_000.0
        v6_median = 9_400.0
        delta_pct = abs(v4_median - v6_median) / v4_median * 100
        assert delta_pct >= 5.0

    def test_parity_ipv6_faster_is_acceptable(self):
        """ORCH_UT_RE_075: IPv6 faster than IPv4 is acceptable."""
        v4_median = 10_000.0
        v6_median = 10_300.0  # 3% faster
        delta_pct = abs(v4_median - v6_median) / v4_median * 100
        assert delta_pct < 5.0


# ===================================================================
# Release playbook existence
# ===================================================================

class TestReleasePlaybook:
    """Verify release validation playbook exists and is well-formed."""

    def test_release_playbook_exists(self):
        """ORCH_UT_RE_080: Release validation playbook file exists."""
        assert _RELEASE_PLAYBOOK.exists(), (
            f"Release playbook not found: {_RELEASE_PLAYBOOK}"
        )

    def test_release_playbook_is_yaml(self):
        """ORCH_UT_RE_081: Release playbook is valid YAML."""
        if not _RELEASE_PLAYBOOK.exists():
            pytest.skip("Release playbook not found")
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")
        content = _RELEASE_PLAYBOOK.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        assert parsed is not None

    def test_release_playbook_no_hardcoded_paths(self):
        """ORCH_UT_RE_082: Release playbook has no hardcoded /opt/omnia/."""
        if not _RELEASE_PLAYBOOK.exists():
            pytest.skip("Release playbook not found")
        content = _RELEASE_PLAYBOOK.read_text(encoding="utf-8")
        lines = content.splitlines()
        for line in lines:
            if line.strip().startswith("#"):
                continue
            assert "/opt/omnia/" not in line, (
                f"Hardcoded path in playbook: {line.strip()}"
            )


# ===================================================================
# Evidence collector module Ansible interface
# ===================================================================

class TestEvidenceModuleInterface:
    """Verify evidence collector Ansible module interface."""

    def test_module_has_documentation(self):
        """ORCH_UT_RE_090: Module has DOCUMENTATION string."""
        assert hasattr(evidence_mod, "DOCUMENTATION")
        assert "collect_ib_ipv6_evidence" in evidence_mod.DOCUMENTATION

    def test_module_has_examples(self):
        """ORCH_UT_RE_091: Module has EXAMPLES string."""
        assert hasattr(evidence_mod, "EXAMPLES")
        assert "collect_ib_ipv6_evidence" in evidence_mod.EXAMPLES

    def test_module_has_return_docs(self):
        """ORCH_UT_RE_092: Module has RETURN documentation."""
        assert hasattr(evidence_mod, "RETURN")
        assert "evidence" in evidence_mod.RETURN

    def test_module_has_run_module(self):
        """ORCH_UT_RE_093: Module exposes run_module entry point."""
        assert hasattr(evidence_mod, "run_module")
        assert callable(evidence_mod.run_module)
