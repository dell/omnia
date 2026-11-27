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
"""Unit tests for validate_ib_ipv6_allocation Ansible module (Issue #5745).

Verifies that dual-stack rows without IB_IPV6 are rejected instead of silently accepted.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
import sys
from unittest import mock

import pytest

# Path setup — add orchestrator plugin module_utils to Python path
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLUGIN_ROOT = _REPO_ROOT / "src" / "orchestrator" / "plugins"
_MODULE_UTILS = _PLUGIN_ROOT / "module_utils"

for _p in (str(_PLUGIN_ROOT), str(_PLUGIN_ROOT / "modules"), str(_MODULE_UTILS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

sys.modules.setdefault("ansible", mock.MagicMock())
sys.modules.setdefault("ansible.module_utils", mock.MagicMock())
sys.modules.setdefault("ansible.module_utils.basic", mock.MagicMock())

import validate_ib_ipv6_allocation  # noqa: E402

LOGGER = logging.getLogger("test_validate_ib_ipv6_allocation")
pytestmark = pytest.mark.unit


class TestDualStackAddressCompleteness:
    """Tests enforcing that dual-stack allocations require both IPv4 and IPv6."""

    def test_dual_stack_explicit_mode_rejects_missing_ib_ipv6(self):
        """OMN-DEF #5745: Dual-stack mode must reject rows missing IB_IPV6."""
        ib_rows = [
            {
                "HOSTNAME": "node01",
                "SERVICE_TAG": "TAG01",
                "IB_NIC_NAME": "InfiniBand.Slot.7-1",
                "IB_IPV4": "192.168.0.1",
                "IB_IPV6": "fd00:1b::1/64",
            },
            {
                "HOSTNAME": "node02",
                "SERVICE_TAG": "TAG02",
                "IB_NIC_NAME": "InfiniBand.Slot.7-1",
                "IB_IPV4": "192.168.0.2",
                "IB_IPV6": "",  # Missing IB_IPV6
            },
        ]
        normalized, errors, mode = validate_ib_ipv6_allocation._pxe_rows_to_normalized(
            ib_rows, [], LOGGER, ib_addr_mode="dual-stack"
        )
        assert mode == "dual-stack"
        assert len(errors) == 1
        assert "node02/InfiniBand.Slot.7-1" in errors[0]
        assert "IB_IPV6 is missing in dual-stack mode" in errors[0]

    def test_dual_stack_explicit_mode_rejects_missing_ib_ipv4(self):
        """OMN-DEF #5745: Dual-stack mode must reject rows missing IB_IPV4."""
        ib_rows = [
            {
                "HOSTNAME": "node01",
                "SERVICE_TAG": "TAG01",
                "IB_NIC_NAME": "InfiniBand.Slot.7-1",
                "IB_IPV4": "",  # Missing IB_IPV4
                "IB_IPV6": "fd00:1b::1/64",
            },
        ]
        normalized, errors, mode = validate_ib_ipv6_allocation._pxe_rows_to_normalized(
            ib_rows, [], LOGGER, ib_addr_mode="dual-stack"
        )
        assert mode == "dual-stack"
        assert len(errors) == 1
        assert "node01/InfiniBand.Slot.7-1" in errors[0]
        assert "IB_IPV4 is missing in dual-stack mode" in errors[0]

    def test_dual_stack_inferred_mode_rejects_missing_ib_ipv6(self):
        """OMN-DEF #5745: Inferred dual-stack mode must reject rows missing IB_IPV6."""
        ib_rows = [
            {
                "HOSTNAME": "node01",
                "SERVICE_TAG": "TAG01",
                "IB_NIC_NAME": "InfiniBand.Slot.7-1",
                "IB_IPV4": "192.168.0.1",
                "IB_IPV6": "fd00:1b::1/64",
            },
            {
                "HOSTNAME": "node02",
                "SERVICE_TAG": "TAG02",
                "IB_NIC_NAME": "InfiniBand.Slot.7-1",
                "IB_IPV4": "192.168.0.2",
                "IB_IPV6": "",  # Missing IB_IPV6
            },
        ]
        # ib_addr_mode is not explicitly specified (empty string)
        normalized, errors, mode = validate_ib_ipv6_allocation._pxe_rows_to_normalized(
            ib_rows, [], LOGGER, ib_addr_mode=""
        )
        assert mode == "dual-stack"
        assert len(errors) == 1
        assert "node02/InfiniBand.Slot.7-1" in errors[0]
        assert "IB_IPV6 is missing in dual-stack mode" in errors[0]

    def test_dual_stack_valid_passes_cleanly(self):
        """Valid dual-stack rows with both IPv4 and IPv6 pass without errors."""
        ib_rows = [
            {
                "HOSTNAME": "node01",
                "SERVICE_TAG": "TAG01",
                "IB_NIC_NAME": "InfiniBand.Slot.7-1",
                "IB_IPV4": "192.168.0.1",
                "IB_IPV6": "fd00:1b::1/64",
            },
            {
                "HOSTNAME": "node02",
                "SERVICE_TAG": "TAG02",
                "IB_NIC_NAME": "InfiniBand.Slot.7-1",
                "IB_IPV4": "192.168.0.2",
                "IB_IPV6": "fd00:1b::2/64",
            },
        ]
        normalized, errors, mode = validate_ib_ipv6_allocation._pxe_rows_to_normalized(
            ib_rows, [], LOGGER, ib_addr_mode="dual-stack"
        )
        assert mode == "dual-stack"
        assert errors == []
        assert "node01" in normalized and "node02" in normalized
        assert len(normalized["node01"]["InfiniBand.Slot.7-1"]) == 2

    def test_ipv6_only_mode_rejects_missing_ib_ipv6(self):
        """IPv6-only mode must reject rows missing IB_IPV6."""
        ib_rows = [
            {
                "HOSTNAME": "node01",
                "SERVICE_TAG": "TAG01",
                "IB_NIC_NAME": "InfiniBand.Slot.7-1",
                "IB_IPV4": "192.168.0.1",
                "IB_IPV6": "",  # Missing IB_IPV6
            },
        ]
        normalized, errors, mode = validate_ib_ipv6_allocation._pxe_rows_to_normalized(
            ib_rows, [], LOGGER, ib_addr_mode="ipv6-only"
        )
        assert mode == "ipv6-only"
        assert len(errors) == 1
        assert "IB_IPV6 is missing in ipv6-only mode" in errors[0]

    def test_ipv4_only_mode_rejects_missing_ib_ipv4(self):
        """IPv4-only mode must reject rows missing IB_IPV4."""
        ib_rows = [
            {
                "HOSTNAME": "node01",
                "SERVICE_TAG": "TAG01",
                "IB_NIC_NAME": "InfiniBand.Slot.7-1",
                "IB_IPV4": "",  # Missing IB_IPV4
                "IB_IPV6": "fd00:1b::1/64",
            },
        ]
        normalized, errors, mode = validate_ib_ipv6_allocation._pxe_rows_to_normalized(
            ib_rows, [], LOGGER, ib_addr_mode="ipv4-only"
        )
        assert mode == "ipv4-only"
        assert len(errors) == 1
        assert "IB_IPV4 is missing in ipv4-only mode" in errors[0]

    def test_end_to_end_pxe_file_parsing_with_dual_stack(self, tmp_path):
        """End-to-end PXE file parsing detects dual-stack and rejects missing IB_IPV6."""
        pxe_file = tmp_path / "pxe_mapping_file.csv"
        headers = [
            "FUNCTIONAL_GROUP_NAME", "GROUP_NAME", "SERVICE_TAG",
            "PARENT_SERVICE_TAG", "HOSTNAME", "ADMIN_MAC", "ADMIN_IP",
            "BMC_MAC", "BMC_IP", "IB_NIC_NAME", "IB_IPV4", "IB_IPV6",
        ]
        rows = [
            [
                "slurm_node_rhel_10_0_x86_64", "grp1", "TAG01", "",
                "node01", "aa:bb:cc:dd:ee:01", "172.16.107.1",
                "aa:bb:cc:dd:ff:01", "172.17.107.1",
                "InfiniBand.Slot.7-1", "192.168.0.1", "fd00:1b::1/64",
            ],
            [
                "slurm_node_rhel_10_0_x86_64", "grp1", "TAG02", "",
                "node02", "aa:bb:cc:dd:ee:02", "172.16.107.2",
                "aa:bb:cc:dd:ff:02", "172.17.107.2",
                "InfiniBand.Slot.7-1", "192.168.0.2", "",  # Missing IB_IPV6
            ],
        ]
        with open(pxe_file, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            writer.writerows(rows)

        ib_rows, parse_errors = validate_ib_ipv6_allocation._parse_pxe_mapping_ib_rows(
            str(pxe_file), LOGGER
        )
        assert parse_errors == []
        assert len(ib_rows) == 2

        normalized, errors, mode = validate_ib_ipv6_allocation._pxe_rows_to_normalized(
            ib_rows, [], LOGGER, ib_addr_mode="dual-stack"
        )
        assert mode == "dual-stack"
        assert len(errors) == 1
        assert "node02/InfiniBand.Slot.7-1" in errors[0]
        assert "IB_IPV6 is missing in dual-stack mode" in errors[0]
