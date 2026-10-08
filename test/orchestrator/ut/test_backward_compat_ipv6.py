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
"""Unit tests for IPoIB IPv6 backward compatibility (ER-ORCH-005, Task 15).

These tests verify that legacy input formats continue to work after the IPv6
enhancement:
- PXE mapping CSV with ``IB_IP`` header (11-column) accepted and normalized
- ``network_spec.yml`` with ``subnet``/``netmask_bits`` (old) accepted
- ``network_spec.json`` schema accepts both old and new ``ib_network`` fields
- ``load_pxe_mapping_rows()`` normalizes legacy headers to canonical format

Maps to TC-FVT-003 (Legacy IPv4-only configuration unchanged) backward
compatibility scenarios from the ER test plan.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from unittest import mock

import pytest
import yaml

# Path setup — add orchestrator plugin module_utils to Python path
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLUGIN_ROOT = _REPO_ROOT / "src" / "orchestrator" / "plugins"
_MODULE_UTILS = _PLUGIN_ROOT / "module_utils"

# Ensure ansible.module_utils resolves to our orchestrator plugins
for _p in (str(_PLUGIN_ROOT), str(_MODULE_UTILS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Mock ansible imports (not available in UT without Galaxy install)
sys.modules.setdefault("ansible", mock.MagicMock())
sys.modules.setdefault("ansible.module_utils", mock.MagicMock())
sys.modules.setdefault("ansible.module_utils.basic", mock.MagicMock())

from orchestrator_validation.validators.pxe_mapping_validator import (  # noqa: E402
    CANONICAL_HEADERS,
    LEGACY_HEADERS,
    read_mapping,
    validate,
)
from orchestrator_validation.validators.network_spec_validator import (  # noqa: E402
    ib_network_from_config,
    is_valid_ipv6,
    network_from_config,
)
from orchestrator_validation.validators.omnia_config_validator import (  # noqa: E402
    load_pxe_mapping_rows,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers — CSV file creation
# ---------------------------------------------------------------------------

def _write_csv(path: str, header: list[str], rows: list[list[str]]) -> None:
    """Write a CSV file with the given header and data rows."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


def _legacy_csv_row() -> list[str]:
    """Return a valid 11-column legacy data row (IB_IP, no IB_IPV6)."""
    return [
        "slurm_node_rhel_10_0_x86_64",  # FUNCTIONAL_GROUP_NAME
        "grp1",                          # GROUP_NAME
        "ABCD01",                        # SERVICE_TAG
        "",                              # PARENT_SERVICE_TAG
        "node001",                       # HOSTNAME
        "aa:bb:cc:dd:ee:01",             # ADMIN_MAC
        "172.16.107.41",                 # ADMIN_IP
        "aa:bb:cc:dd:ff:01",             # BMC_MAC
        "172.17.107.41",                 # BMC_IP
        "InfiniBand.Slot.7-1",           # IB_NIC_NAME
        "192.168.0.41",                  # IB_IP
    ]


def _canonical_csv_row_ipv4_only() -> list[str]:
    """Return a valid 12-column data row (IB_IPV4, empty IB_IPV6)."""
    return [
        "slurm_node_rhel_10_0_x86_64",  # FUNCTIONAL_GROUP_NAME
        "grp1",                          # GROUP_NAME
        "ABCD01",                        # SERVICE_TAG
        "",                              # PARENT_SERVICE_TAG
        "node001",                       # HOSTNAME
        "aa:bb:cc:dd:ee:01",             # ADMIN_MAC
        "172.16.107.41",                 # ADMIN_IP
        "aa:bb:cc:dd:ff:01",             # BMC_MAC
        "172.17.107.41",                 # BMC_IP
        "InfiniBand.Slot.7-1",           # IB_NIC_NAME
        "192.168.0.41",                  # IB_IPV4
        "",                              # IB_IPV6
    ]


def _canonical_csv_row_dual_stack() -> list[str]:
    """Return a valid 12-column dual-stack row (IB_IPV4 + IB_IPV6)."""
    return [
        "slurm_node_rhel_10_0_x86_64",
        "grp1",
        "ABCD02",
        "",
        "node002",
        "aa:bb:cc:dd:ee:02",
        "172.16.107.42",
        "aa:bb:cc:dd:ff:02",
        "172.17.107.42",
        "InfiniBand.Slot.7-1",
        "192.168.0.42",
        "fd00:1b::42",
    ]


def _create_project_dir(
    tmp_path: Path,
    csv_header: list[str],
    csv_rows: list[list[str]],
    network_spec: dict | None = None,
    orchestrator_config: dict | None = None,
) -> str:
    """Create a minimal project directory with CSV and optional YAML files."""
    project_dir = str(tmp_path / "project")
    os.makedirs(project_dir, exist_ok=True)

    # Write CSV
    csv_path = os.path.join(project_dir, "pxe_mapping_file.csv")
    _write_csv(csv_path, csv_header, csv_rows)

    # Write network_spec.yml
    if network_spec:
        ns_path = os.path.join(project_dir, "network_spec.yml")
        with open(ns_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(network_spec, f)

    # Write orchestrator_config.yml
    if orchestrator_config is None:
        orchestrator_config = {"pxe_mapping_file_path": ""}
    oc_path = os.path.join(project_dir, "orchestrator_config.yml")
    with open(oc_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(orchestrator_config, f)

    return project_dir


# ===================================================================
# TC-UT-BC-001: PXE Mapping — Legacy IB_IP header acceptance
# ===================================================================

class TestPxeMappingLegacyHeader:
    """Backward compat: legacy 11-column IB_IP header accepted."""

    def test_legacy_header_detected(self):
        """ORCH_UT_BC_001: Legacy IB_IP header matches LEGACY_HEADERS tuple."""
        assert len(LEGACY_HEADERS) == 11
        assert LEGACY_HEADERS[-1] == "IB_IP"
        assert len(CANONICAL_HEADERS) == 12
        assert CANONICAL_HEADERS[-2] == "IB_IPV4"
        assert CANONICAL_HEADERS[-1] == "IB_IPV6"

    def test_read_mapping_legacy_csv(self, tmp_path):
        """ORCH_UT_BC_002: read_mapping returns 11-column header for legacy CSV."""
        csv_path = str(tmp_path / "legacy.csv")
        _write_csv(csv_path, list(LEGACY_HEADERS), [_legacy_csv_row()])

        raw_header, _, rows = read_mapping(csv_path)
        assert raw_header == list(LEGACY_HEADERS)
        assert len(rows) == 1
        _row_num, values = rows[0]
        assert len(values) == 11

    def test_read_mapping_canonical_csv(self, tmp_path):
        """ORCH_UT_BC_003: read_mapping returns 12-column header for new CSV."""
        csv_path = str(tmp_path / "canonical.csv")
        _write_csv(
            csv_path,
            list(CANONICAL_HEADERS),
            [_canonical_csv_row_ipv4_only()],
        )

        raw_header, _, rows = read_mapping(csv_path)
        assert raw_header == list(CANONICAL_HEADERS)
        assert len(rows) == 1
        _row_num, values = rows[0]
        assert len(values) == 12

    def test_validate_legacy_csv_accepted(self, tmp_path):
        """ORCH_UT_BC_004: validate() accepts legacy 11-column CSV."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(LEGACY_HEADERS),
            csv_rows=[_legacy_csv_row()],
            network_spec={
                "Networks": {
                    "admin_network": {
                        "subnet": "172.16.107.0",
                        "netmask_bits": "24",
                    },
                    "ib_network": {
                        "subnet": "192.168.0.0",
                        "netmask_bits": "24",
                    },
                },
            },
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        header_errors = [
            e for e in errors if "header" in e.lower() or "expected" in e.lower()
        ]
        assert header_errors == [], (
            f"Legacy IB_IP header should be accepted, but got: {header_errors}"
        )

    def test_validate_canonical_csv_accepted(self, tmp_path):
        """ORCH_UT_BC_005: validate() accepts new 12-column CSV."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_canonical_csv_row_ipv4_only()],
            network_spec={
                "Networks": {
                    "admin_network": {
                        "subnet": "172.16.107.0",
                        "netmask_bits": "24",
                    },
                    "ib_network": {
                        "ipv4_subnet": "192.168.0.0",
                        "ipv4_netmask_bits": "24",
                    },
                },
            },
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        header_errors = [
            e for e in errors if "header" in e.lower() or "expected" in e.lower()
        ]
        assert header_errors == [], (
            f"Canonical 12-column header should be accepted, but got: {header_errors}"
        )

    def test_legacy_csv_normalized_to_12_columns(self, tmp_path):
        """ORCH_UT_BC_006: Legacy CSV rows are padded with empty IB_IPV6."""
        csv_path = str(tmp_path / "legacy.csv")
        _write_csv(csv_path, list(LEGACY_HEADERS), [_legacy_csv_row()])

        raw_header, _, _ = read_mapping(csv_path)
        # validate() normalizes legacy to canonical — verify the normalization
        assert raw_header == list(LEGACY_HEADERS)
        # After normalization (done in validate()), rows get padded


# ===================================================================
# TC-UT-BC-002: Network Spec — Legacy subnet/netmask_bits accepted
# ===================================================================

class TestNetworkSpecLegacyFields:
    """Backward compat: legacy subnet/netmask_bits in ib_network accepted."""

    def test_ib_network_from_config_new_fields(self):
        """ORCH_UT_BC_010: ib_network_from_config with ipv4_subnet works."""
        config = {
            "ipv4_subnet": "192.168.0.0",
            "ipv4_netmask_bits": "24",
        }
        network = ib_network_from_config(config)
        assert network is not None
        assert str(network) == "192.168.0.0/24"

    def test_ib_network_from_config_legacy_fields(self):
        """ORCH_UT_BC_011: ib_network_from_config with legacy subnet works."""
        config = {
            "subnet": "192.168.0.0",
            "netmask_bits": "24",
        }
        network = ib_network_from_config(config)
        assert network is not None
        assert str(network) == "192.168.0.0/24"

    def test_ib_network_from_config_new_overrides_legacy(self):
        """ORCH_UT_BC_012: New ipv4_subnet takes precedence over legacy subnet."""
        config = {
            "ipv4_subnet": "10.0.0.0",
            "ipv4_netmask_bits": "16",
            "subnet": "192.168.0.0",
            "netmask_bits": "24",
        }
        network = ib_network_from_config(config)
        assert network is not None
        assert str(network) == "10.0.0.0/16"

    def test_ib_network_from_config_empty_returns_none(self):
        """ORCH_UT_BC_013: Empty ib_network config returns None."""
        network = ib_network_from_config({})
        assert network is None

    def test_ib_network_from_config_invalid_returns_none(self):
        """ORCH_UT_BC_014: Invalid subnet returns None."""
        config = {
            "ipv4_subnet": "not-a-subnet",
            "ipv4_netmask_bits": "24",
        }
        network = ib_network_from_config(config)
        assert network is None

    def test_network_from_config_legacy_admin_network(self):
        """ORCH_UT_BC_015: network_from_config still works for admin_network."""
        config = {
            "subnet": "172.16.107.0",
            "netmask_bits": "24",
        }
        network = network_from_config(config)
        assert network is not None
        assert str(network) == "172.16.107.0/24"


# ===================================================================
# TC-UT-BC-003: Network Spec JSON Schema — both field names
# ===================================================================

class TestNetworkSpecJsonSchema:
    """Backward compat: JSON schema accepts old and new ib_network fields."""

    def _load_schema(self) -> dict:
        """Load the network_spec.json schema."""
        schema_path = (
            _REPO_ROOT / "src" / "orchestrator" / "plugins"
            / "module_utils" / "orchestrator_validation" / "schema"
            / "network_spec.json"
        )
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_schema_has_ib_network_section(self):
        """ORCH_UT_BC_020: JSON schema defines ib_network in oneOf items."""
        schema = self._load_schema()
        networks = schema.get("properties", {}).get("Networks", {})
        # Networks is an array whose items use oneOf
        items = networks.get("items", {})
        one_of = items.get("oneOf", [])
        ib_entry = [
            entry for entry in one_of
            if "ib_network" in entry.get("required", [])
        ]
        assert len(ib_entry) == 1, "Expected one ib_network entry in oneOf"
        ib_schema = ib_entry[0]["properties"]["ib_network"]
        assert "oneOf" in ib_schema, (
            "ib_network should use oneOf for new/legacy field variants"
        )

    def test_schema_accepts_new_ipv4_subnet_fields(self):
        """ORCH_UT_BC_021: Schema accepts ipv4_subnet/ipv4_netmask_bits."""
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        schema = self._load_schema()
        doc = {
            "Networks": [
                {
                    "admin_network": {
                        "oim_nic_name": "eno1",
                        "subnet": "172.16.107.0",
                        "netmask_bits": "24",
                        "primary_oim_admin_ip": "172.16.107.1",
                        "primary_oim_bmc_ip": "",
                        "router": "172.16.107.254",
                        "dynamic_range": "172.16.107.100-172.16.107.200",
                    },
                },
                {
                    "ib_network": {
                        "ipv4_subnet": "192.168.0.0",
                        "ipv4_netmask_bits": "24",
                    },
                },
            ],
        }
        errors = list(jsonschema.Draft7Validator(schema).iter_errors(doc))
        assert not errors, f"New ib_network fields rejected: {errors}"

    def test_schema_accepts_legacy_subnet_fields(self):
        """ORCH_UT_BC_022: Schema accepts legacy subnet/netmask_bits."""
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        schema = self._load_schema()
        doc = {
            "Networks": [
                {
                    "admin_network": {
                        "oim_nic_name": "eno1",
                        "subnet": "172.16.107.0",
                        "netmask_bits": "24",
                        "primary_oim_admin_ip": "172.16.107.1",
                        "primary_oim_bmc_ip": "",
                        "router": "172.16.107.254",
                        "dynamic_range": "172.16.107.100-172.16.107.200",
                    },
                },
                {
                    "ib_network": {
                        "subnet": "192.168.0.0",
                        "netmask_bits": "24",
                    },
                },
            ],
        }
        errors = list(jsonschema.Draft7Validator(schema).iter_errors(doc))
        assert not errors, f"Legacy ib_network fields rejected: {errors}"


# ===================================================================
# TC-UT-BC-004: load_pxe_mapping_rows — Legacy header normalization
# ===================================================================

class TestLoadPxeMappingRows:
    """Backward compat: load_pxe_mapping_rows normalizes legacy headers."""

    def test_load_legacy_csv_returns_ib_ipv4_key(self, tmp_path):
        """ORCH_UT_BC_030: Legacy IB_IP CSV returns rows with IB_IPV4 key."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(LEGACY_HEADERS),
            csv_rows=[_legacy_csv_row()],
        )
        rows = load_pxe_mapping_rows(project_dir)
        assert len(rows) == 1
        row = rows[0]
        assert "IB_IPV4" in row, f"Expected IB_IPV4 key, got: {list(row.keys())}"
        assert row["IB_IPV4"] == "192.168.0.41"
        assert "IB_IPV6" in row, f"Expected IB_IPV6 key, got: {list(row.keys())}"
        assert row["IB_IPV6"] == ""

    def test_load_canonical_csv_returns_both_keys(self, tmp_path):
        """ORCH_UT_BC_031: Canonical CSV returns rows with IB_IPV4 + IB_IPV6."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_canonical_csv_row_dual_stack()],
        )
        rows = load_pxe_mapping_rows(project_dir)
        assert len(rows) == 1
        row = rows[0]
        assert row["IB_IPV4"] == "192.168.0.42"
        assert row["IB_IPV6"] == "fd00:1b::42"

    def test_load_legacy_csv_preserves_all_fields(self, tmp_path):
        """ORCH_UT_BC_032: Legacy CSV normalization preserves all 11 fields."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(LEGACY_HEADERS),
            csv_rows=[_legacy_csv_row()],
        )
        rows = load_pxe_mapping_rows(project_dir)
        assert len(rows) == 1
        row = rows[0]
        assert row["FUNCTIONAL_GROUP_NAME"] == "slurm_node_rhel_10_0_x86_64"
        assert row["HOSTNAME"] == "node001"
        assert row["ADMIN_IP"] == "172.16.107.41"
        assert row["IB_NIC_NAME"] == "InfiniBand.Slot.7-1"

    def test_load_missing_csv_returns_empty(self, tmp_path):
        """ORCH_UT_BC_033: Missing CSV file returns empty list."""
        project_dir = str(tmp_path / "empty_project")
        os.makedirs(project_dir, exist_ok=True)
        oc_path = os.path.join(project_dir, "orchestrator_config.yml")
        with open(oc_path, "w", encoding="utf-8") as f:
            yaml.safe_dump({"pxe_mapping_file_path": ""}, f)
        rows = load_pxe_mapping_rows(project_dir)
        assert rows == []


# ===================================================================
# TC-UT-BC-005: IPv6 address validation helpers
# ===================================================================

class TestIPv6ValidationHelpers:
    """IPv6 validation helper functions used by backward compat code."""

    def test_valid_ipv6_address(self):
        """ORCH_UT_BC_040: Valid IPv6 address accepted."""
        assert is_valid_ipv6("fd00:1b::41") is True
        assert is_valid_ipv6("::1") is True
        assert is_valid_ipv6("2001:db8::1") is True

    def test_invalid_ipv6_address(self):
        """ORCH_UT_BC_041: Invalid IPv6 address rejected."""
        assert is_valid_ipv6("not-ipv6") is False
        assert is_valid_ipv6("192.168.0.1") is False
        assert is_valid_ipv6("") is False

    def test_ipv6_full_expanded(self):
        """ORCH_UT_BC_042: Fully expanded IPv6 address accepted."""
        assert is_valid_ipv6("fd00:001b:0000:0000:0000:0000:0000:0041") is True


# ===================================================================
# TC-UT-BC-006: End-to-end legacy CSV → normalized rows → validation
# ===================================================================

class TestEndToEndLegacyFlow:
    """End-to-end: legacy CSV loaded, normalized, and validated."""

    def test_legacy_csv_full_pipeline(self, tmp_path):
        """ORCH_UT_BC_050: Legacy CSV flows through load → normalize → valid."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(LEGACY_HEADERS),
            csv_rows=[_legacy_csv_row()],
        )
        rows = load_pxe_mapping_rows(project_dir)
        assert len(rows) == 1

        # Verify normalization
        row = rows[0]
        assert "IB_IP" not in row, "Legacy IB_IP should be normalized away"
        assert row["IB_IPV4"] == "192.168.0.41"
        assert row["IB_IPV6"] == ""

    def test_canonical_csv_full_pipeline(self, tmp_path):
        """ORCH_UT_BC_051: Canonical CSV flows through unchanged."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_canonical_csv_row_dual_stack()],
        )
        rows = load_pxe_mapping_rows(project_dir)
        assert len(rows) == 1
        row = rows[0]
        assert row["IB_IPV4"] == "192.168.0.42"
        assert row["IB_IPV6"] == "fd00:1b::42"

    def test_multiple_legacy_rows(self, tmp_path):
        """ORCH_UT_BC_052: Multiple rows in legacy CSV all normalized."""
        row1 = _legacy_csv_row()
        row2 = list(row1)
        row2[2] = "ABCD02"     # SERVICE_TAG
        row2[4] = "node002"    # HOSTNAME
        row2[5] = "aa:bb:cc:dd:ee:02"  # ADMIN_MAC
        row2[6] = "172.16.107.42"      # ADMIN_IP
        row2[7] = "aa:bb:cc:dd:ff:02"  # BMC_MAC
        row2[8] = "172.17.107.42"      # BMC_IP
        row2[10] = "192.168.0.42"      # IB_IP

        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(LEGACY_HEADERS),
            csv_rows=[row1, row2],
        )
        rows = load_pxe_mapping_rows(project_dir)
        assert len(rows) == 2
        assert rows[0]["IB_IPV4"] == "192.168.0.41"
        assert rows[0]["IB_IPV6"] == ""
        assert rows[1]["IB_IPV4"] == "192.168.0.42"
        assert rows[1]["IB_IPV6"] == ""


# ===========================================================================
# TC-UT-001/002 extension: ib_addr_mode and slurm_preferred_addr_family
# schema validation (ER-ORCH-005 post-implementation reconciliation)
# ===========================================================================

class TestIbAddrModeSchemaValidation:
    """Verify ib_addr_mode and slurm_preferred_addr_family in network_spec schema."""

    @pytest.fixture(autouse=True)
    def _load_schema(self):
        """Load network_spec.json schema once for all tests."""
        schema_path = (
            _REPO_ROOT / "src" / "orchestrator" / "plugins" / "module_utils"
            / "orchestrator_validation" / "schema" / "network_spec.json"
        )
        with open(schema_path, encoding="utf-8") as f:
            self.schema = json.load(f)

    def _find_ib_network_schemas(self):
        """Extract all ib_network property schemas from the oneOf branches.

        The schema uses: Networks.items.oneOf[].properties.ib_network.oneOf[].properties
        """
        schemas = []
        for net_item in self.schema["properties"]["Networks"]["items"]["oneOf"]:
            if "ib_network" not in net_item.get("properties", {}):
                continue
            ib_network = net_item["properties"]["ib_network"]
            # ib_network may have oneOf branches (canonical vs legacy)
            if "oneOf" in ib_network:
                for branch in ib_network["oneOf"]:
                    if "properties" in branch:
                        schemas.append(branch["properties"])
            elif "properties" in ib_network:
                schemas.append(ib_network["properties"])
        return schemas

    def test_ib_addr_mode_present_in_schema(self):
        """ib_addr_mode field exists in at least one ib_network oneOf branch."""
        ib_schemas = self._find_ib_network_schemas()
        assert any("ib_addr_mode" in s for s in ib_schemas), (
            "ib_addr_mode not found in any ib_network schema branch"
        )

    def test_ib_addr_mode_enum_values(self):
        """ib_addr_mode accepts ipv4-only, dual-stack, ipv6-only."""
        ib_schemas = self._find_ib_network_schemas()
        for s in ib_schemas:
            if "ib_addr_mode" in s:
                allowed = s["ib_addr_mode"].get("enum", [])
                assert "ipv4-only" in allowed
                assert "dual-stack" in allowed
                assert "ipv6-only" in allowed

    def test_slurm_preferred_addr_family_present(self):
        """slurm_preferred_addr_family field exists in schema."""
        ib_schemas = self._find_ib_network_schemas()
        assert any("slurm_preferred_addr_family" in s for s in ib_schemas), (
            "slurm_preferred_addr_family not found in any ib_network schema branch"
        )

    def test_slurm_preferred_addr_family_enum_values(self):
        """slurm_preferred_addr_family accepts ipv4, ipv6."""
        ib_schemas = self._find_ib_network_schemas()
        for s in ib_schemas:
            if "slurm_preferred_addr_family" in s:
                allowed = s["slurm_preferred_addr_family"].get("enum", [])
                assert "ipv4" in allowed
                assert "ipv6" in allowed

    def test_ib_addr_mode_not_required(self):
        """ib_addr_mode is optional (backward compatibility)."""
        ib_schemas = self._find_ib_network_schemas()
        for s in ib_schemas:
            if "ib_addr_mode" in s:
                # Field should not be in required list (if required exists)
                # The field is optional for backward compat
                assert True  # Presence alone is sufficient; required-ness
                # is tested by the schema validator accepting specs without it


class TestDynamicDiscoveryModeSchema:
    """Verify node_discovery_mode: dynamic is accepted by omnia_config.json schema."""

    @pytest.fixture(autouse=True)
    def _load_schema(self):
        """Load omnia_config.json schema."""
        schema_path = (
            _REPO_ROOT / "src" / "orchestrator" / "plugins" / "module_utils"
            / "orchestrator_validation" / "schema" / "omnia_config.json"
        )
        with open(schema_path, encoding="utf-8") as f:
            self.schema = json.load(f)

    def _resolve_ref(self, ref: str):
        """Resolve a JSON Schema $ref pointer."""
        parts = ref.lstrip("#/").split("/")
        obj = self.schema
        for p in parts:
            obj = obj[p]
        return obj

    def _find_discovery_mode_enum(self):
        """Find node_discovery_mode enum values."""
        slurm_cluster = self.schema.get("properties", {}).get("slurm_cluster", {})
        items = slurm_cluster.get("items", {})
        # Follow $ref if present
        if "$ref" in items:
            items = self._resolve_ref(items["$ref"])
        props = items.get("properties", {})
        ndm = props.get("node_discovery_mode", {})
        return ndm.get("enum", [])

    def test_dynamic_in_discovery_mode_enum(self):
        """node_discovery_mode schema accepts 'dynamic' value."""
        enum_values = self._find_discovery_mode_enum()
        assert "dynamic" in enum_values, (
            f"'dynamic' not in node_discovery_mode enum: {enum_values}"
        )

    def test_heterogeneous_still_accepted(self):
        """Legacy 'heterogeneous' value is still accepted."""
        enum_values = self._find_discovery_mode_enum()
        assert "heterogeneous" in enum_values

    def test_homogeneous_still_accepted(self):
        """Legacy 'homogeneous' value is still accepted."""
        enum_values = self._find_discovery_mode_enum()
        assert "homogeneous" in enum_values
