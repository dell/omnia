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
"""Unit tests for PXE mapping hostname validation.

These tests verify that hostname validation correctly handles:
- Custom hostnames when dns_enabled=True
- NID format hostnames (nid followed by digits)
- Edge cases like nid-prefixed custom names
- Mixed nid/custom hostnames in the same mapping file
- Rejection of invalid hostnames
"""

from __future__ import annotations

import csv
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
    validate,
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


def _create_project_dir(
    tmp_path: Path,
    csv_header: list[str],
    csv_rows: list[list[str]],
    dns_enabled: bool = True,
) -> str:
    """Create a minimal project directory with CSV and config files."""
    project_dir = str(tmp_path / "project")
    os.makedirs(project_dir, exist_ok=True)

    # Write CSV (mode 0o640 required by the PXE mapping file validator)
    csv_path = os.path.join(project_dir, "pxe_mapping_file.csv")
    _write_csv(csv_path, csv_header, csv_rows)
    os.chmod(csv_path, 0o640)

    # Write orchestrator_config.yml
    orchestrator_config = {
        "pxe_mapping_file_path": "",
        "dns_enabled": dns_enabled,
    }
    oc_path = os.path.join(project_dir, "orchestrator_config.yml")
    with open(oc_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(orchestrator_config, f)

    return project_dir


def _base_csv_row(hostname: str) -> list[str]:
    """Return a valid canonical CSV row with the given hostname."""
    return [
        "slurm_node_rhel_10_0_x86_64",  # FUNCTIONAL_GROUP_NAME
        "grp1",                          # GROUP_NAME
        "ABCD01",                        # SERVICE_TAG
        "",                              # PARENT_SERVICE_TAG
        hostname,                        # HOSTNAME
        "aa:bb:cc:dd:ee:01",             # ADMIN_MAC
        "172.16.107.41",                 # ADMIN_IP
        "aa:bb:cc:dd:ff:01",             # BMC_MAC
        "172.17.107.41",                 # BMC_IP
        "",                              # IB_NIC_NAME
        "",                              # IB_IPV4
        "",                              # IB_IPV6
    ]


# ===================================================================
# TC-UT-HN-001: Custom hostnames accepted when dns_enabled=True
# ===================================================================

class TestCustomHostnamesWithDnsEnabled:
    """Custom hostnames should pass validation when dns_enabled=True."""

    def test_custom_hostname_gpu_worker(self, tmp_path):
        """ORCH_UT_HN_001: gpu-worker-01 accepted with dns_enabled=True."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("gpu-worker-01")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"Custom hostname 'gpu-worker-01' should be accepted with dns_enabled=True, "
            f"but got: {hostname_errors}"
        )

    def test_custom_hostname_storage_node(self, tmp_path):
        """ORCH_UT_HN_002: storage-node-a accepted with dns_enabled=True."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("storage-node-a")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"Custom hostname 'storage-node-a' should be accepted with dns_enabled=True, "
            f"but got: {hostname_errors}"
        )

    def test_custom_hostname_login_server(self, tmp_path):
        """ORCH_UT_HN_003: login-server accepted with dns_enabled=True."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("login-server")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"Custom hostname 'login-server' should be accepted with dns_enabled=True, "
            f"but got: {hostname_errors}"
        )


# ===================================================================
# TC-UT-HN-002: NID format hostnames accepted
# ===================================================================

class TestNidFormatHostnames:
    """NID format hostnames (nid followed by digits) should pass validation."""

    def test_nid_single_digit(self, tmp_path):
        """ORCH_UT_HN_010: nid1 accepted with dns_enabled=True."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("nid1")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"NID hostname 'nid1' should be accepted, but got: {hostname_errors}"
        )

    def test_nid_three_digits(self, tmp_path):
        """ORCH_UT_HN_011: nid001 accepted with dns_enabled=True."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("nid001")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"NID hostname 'nid001' should be accepted, but got: {hostname_errors}"
        )

    def test_nid_four_digits(self, tmp_path):
        """ORCH_UT_HN_012: nid1000 accepted with dns_enabled=True."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("nid1000")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"NID hostname 'nid1000' should be accepted (supports large clusters), "
            f"but got: {hostname_errors}"
        )

    def test_nid_large_number(self, tmp_path):
        """ORCH_UT_HN_013: nid6000 accepted with dns_enabled=True."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("nid6000")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"NID hostname 'nid6000' should be accepted (supports 6000-node clusters), "
            f"but got: {hostname_errors}"
        )


# ===================================================================
# TC-UT-HN-003: Edge cases - nid-prefixed custom names
# ===================================================================

class TestNidPrefixedCustomHostnames:
    """Custom hostnames starting with 'nid' should be accepted."""

    def test_nidhogg(self, tmp_path):
        """ORCH_UT_HN_020: nidhogg accepted (custom name starting with nid)."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("nidhogg")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"Custom hostname 'nidhogg' should be accepted, but got: {hostname_errors}"
        )

    def test_nidus_compute(self, tmp_path):
        """ORCH_UT_HN_021: nidus-compute accepted (custom name starting with nid)."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("nidus-compute")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"Custom hostname 'nidus-compute' should be accepted, but got: {hostname_errors}"
        )

    def test_nidserver_01(self, tmp_path):
        """ORCH_UT_HN_022: nidserver-01 accepted (custom name starting with nid)."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("nidserver-01")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"Custom hostname 'nidserver-01' should be accepted, but got: {hostname_errors}"
        )


# ===================================================================
# TC-UT-HN-004: Mixed nid/custom hostnames in same file
# ===================================================================

class TestMixedHostnames:
    """Mixed nid and custom hostnames should both be accepted."""

    def test_mixed_nid_and_custom(self, tmp_path):
        """ORCH_UT_HN_030: Mixed nid001 and gpu-worker-01 in same file."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[
                _base_csv_row("gpu-worker-01"),
                _base_csv_row("nid1000"),
                _base_csv_row("login-server"),
            ],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"Mixed hostnames should be accepted, but got: {hostname_errors}"
        )

    def test_mixed_nid_prefixed_custom(self, tmp_path):
        """ORCH_UT_HN_031: Mixed nidhogg and nid001 in same file."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[
                _base_csv_row("nidhogg"),
                _base_csv_row("nid001"),
                _base_csv_row("nidus-compute"),
            ],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"Mixed nid-prefixed custom and nid format should be accepted, "
            f"but got: {hostname_errors}"
        )


# ===================================================================
# TC-UT-HN-005: Invalid hostnames rejected
# ===================================================================

class TestInvalidHostnames:
    """Invalid hostnames should be rejected regardless of dns_enabled."""

    def test_uppercase_hostname_rejected(self, tmp_path):
        """ORCH_UT_HN_040: GPU-Worker-01 rejected (uppercase)."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("GPU-Worker-01")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert len(hostname_errors) > 0, (
            "Uppercase hostname should be rejected"
        )

    def test_hostname_starting_with_hyphen_rejected(self, tmp_path):
        """ORCH_UT_HN_041: -worker-01 rejected (starts with hyphen)."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("-worker-01")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert len(hostname_errors) > 0, (
            "Hostname starting with hyphen should be rejected"
        )

    def test_hostname_ending_with_hyphen_rejected(self, tmp_path):
        """ORCH_UT_HN_042: worker-01- rejected (ends with hyphen)."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("worker-01-")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert len(hostname_errors) > 0, (
            "Hostname ending with hyphen should be rejected"
        )

    def test_hostname_with_underscore_rejected(self, tmp_path):
        """ORCH_UT_HN_043: worker_01 rejected (contains underscore)."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("worker_01")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert len(hostname_errors) > 0, (
            "Hostname with underscore should be rejected"
        )

    def test_nid0_accepted(self, tmp_path):
        """ORCH_UT_HN_044: nid0 accepted (valid DNS hostname, no NID range restriction)."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("nid0")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"nid0 should be accepted (valid DNS hostname, no NID range restriction), "
            f"but got: {hostname_errors}"
        )

    def test_nid00_accepted(self, tmp_path):
        """ORCH_UT_HN_045: nid00 accepted (valid DNS hostname, no NID range restriction)."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("nid00")],
            dns_enabled=True,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"nid00 should be accepted (valid DNS hostname, no NID range restriction), "
            f"but got: {hostname_errors}"
        )


# ===================================================================
# TC-UT-HN-006: DNS disabled behavior
# ===================================================================

class TestDnsDisabled:
    """When dns_enabled=False, only general hostname pattern applies."""

    def test_custom_hostname_dns_disabled(self, tmp_path):
        """ORCH_UT_HN_050: gpu-worker-01 accepted with dns_enabled=False."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("gpu-worker-01")],
            dns_enabled=False,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"Custom hostname should be accepted with dns_enabled=False, "
            f"but got: {hostname_errors}"
        )

    def test_nid_format_dns_disabled(self, tmp_path):
        """ORCH_UT_HN_051: nid001 accepted with dns_enabled=False."""
        project_dir = _create_project_dir(
            tmp_path,
            csv_header=list(CANONICAL_HEADERS),
            csv_rows=[_base_csv_row("nid001")],
            dns_enabled=False,
        )
        config_data = {
            "pxe_mapping_file_path": "",
            "admin_network_subnet": "172.16.107.0",
            "admin_network_netmask_bits": "24",
        }
        errors = validate(config_data, project_dir)
        hostname_errors = [e for e in errors if "hostname" in e.lower()]
        assert hostname_errors == [], (
            f"NID hostname should be accepted with dns_enabled=False, "
            f"but got: {hostname_errors}"
        )
