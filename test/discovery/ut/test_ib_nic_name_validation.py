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
"""Unit tests for IB_NIC_NAME allowlist regex used across security layers.

The same regex pattern is used in ome_server_inventory.py,
pxe_mapping_validator.py, configure-ib-network.sh.j2, and
pxe_boot_inventory vars. These tests verify the canonical pattern
accepts all known Dell InfiniBand FQDD formats and rejects values
that could lead to command injection in bash declare -A statements.
"""

import re

import pytest

# Canonical pattern — must match _IB_NIC_NAME_RE in ome_server_inventory.py
# and IB_NIC_NAME_PATTERN in pxe_mapping_validator.py.
_IB_NIC_NAME_RE = re.compile(
    r"^(?:(?:InfiniBand\.PCIe\.Slot\.|InfiniBand\.Slot\.|"
    r"NIC\.InfiniBand\.)[0-9A-Fa-f]+-[0-9]+|"
    r"InfiniBand\.Single-[0-9]+)$"
)


@pytest.mark.parametrize(
    "value",
    [
        "InfiniBand.PCIe.Slot.22-1",
        "InfiniBand.PCIe.Slot.b5-1",
        "InfiniBand.PCIe.Slot.B5-1",
        "InfiniBand.PCIe.Slot.0-2",
        "InfiniBand.Slot.7-1",
        "InfiniBand.Slot.a0-1",
        "InfiniBand.Slot.FF-3",
        "NIC.InfiniBand.3-1",
        "NIC.InfiniBand.a-2",
        "InfiniBand.Single-1",
        "InfiniBand.Single-2",
    ],
)
def test_valid_ib_nic_names_pass(value):
    """Valid Dell InfiniBand FQDD formats must pass the allowlist."""
    assert _IB_NIC_NAME_RE.fullmatch(value), f"{value!r} should match"


@pytest.mark.parametrize(
    ("value", "label"),
    [
        ("$(echo pwned)", "command substitution"),
        ("`whoami`", "backtick injection"),
        ("InfiniBand.Slot.7-1$(id)", "payload appended to valid prefix"),
        ("InfiniBand.Slot.7-1; rm -rf /", "semicolon command chain"),
        ('InfiniBand.Slot.7-1"]; echo x; #', "quote breakout"),
        ("InfiniBand.Slot.7-1\necho pwned", "newline injection"),
        ("${IFS}cat${IFS}/etc/passwd", "variable expansion"),
    ],
)
def test_injection_payloads_are_blocked(value, label):
    """Shell metacharacter payloads must never match the allowlist."""
    assert not _IB_NIC_NAME_RE.fullmatch(value), f"{label}: {value!r} should be blocked"


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "NIC.Integrated.1-1-1",
        "Ethernet.Slot.3-1",
        "InfiniBand",
        "InfiniBand.Slot.",
        "InfiniBand.Slot.-1",
        "InfiniBand.Slot.7-",
        "InfiniBand.PCIe.Slot.7-1-extra",
        "infiniBand.Slot.7-1",
    ],
)
def test_malformed_ib_nic_names_are_rejected(value):
    """Non-InfiniBand, incomplete, or case-wrong values must be rejected."""
    assert not _IB_NIC_NAME_RE.fullmatch(value), f"{value!r} should be rejected"
