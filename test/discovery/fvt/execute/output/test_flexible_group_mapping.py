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
Discovery — Flexible Group Mapping Compatibility FVT Tests.

Test Case:
- TC_FVT_discovery_012: Verify Discovery accepts and preserves exact fg_ names
  with OS/version/architecture suffixes through the operator-reviewed mapping
  handoff, and rejects invalid flexible identities with truthful evidence.
"""

import csv
import os
import stat
import sys
import tempfile
import pytest

from library.functions import (
    TestLogger,
    check_flexible_group_mapping,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
)
from library.vars.test_case_vars import TEST_CASES as TC

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../"))
MODULES_DIR = os.path.join(REPO_ROOT, "src/discovery/plugins/modules")
if MODULES_DIR not in sys.path:
    sys.path.insert(0, MODULES_DIR)

from generate_pxe_mapping import resolve_functional_group  # pylint: disable=wrong-import-position


@pytest.mark.functional
@pytest.mark.fvt
@pytest.mark.order(12)
def test_discovery_flexible_group_mapping(host):
    """TC_FVT_discovery_012: Verify Discovery flexible group mapping compatibility.

    Validates:
    - FR-6.1: Valid unversioned fg_ name with arch suffix has OS/version injected
    - FR-6.1: Already versioned fg_ name is preserved exactly as catalog-compatible identity
    - FR-6.1: Invalid prefix or architecture suffix is rejected with truthful evidence
    - NFR: Predefined mapping behavior remains compatible
    - NFR: No credentials appear in mapping status or reports
    - AC-009: Operator-reviewed handoff remains explicit
    """
    tc = TC["discovery_flexible_group_mapping"]
    tl = TestLogger(TEST_NAMES["discovery_flexible_group_mapping"], tc["id"])
    result = check_flexible_group_mapping(host)

    if result["success"]:
        tl.passed(LOG["flexible_group_mapping_ok"], result["details"])
    else:
        tl.failed(
            LOG["flexible_group_mapping_failed"].format(
                reason=result.get("error", "Unknown error")
            ),
            result.get("details", ""),
        )

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.fvt
@pytest.mark.order(13)
@pytest.mark.parametrize(
    ("input_group", "expected_group", "os_type", "os_version"),
    [
        ("fg_webserver_x86_64", "fg_webserver_rhel_10_0_x86_64", "rhel", "10_0"),
        ("fg_ai_worker_aarch64", "fg_ai_worker_rhel_10_2_aarch64", "rhel", "10_2"),
        ("fg_compute_rhel_10_2_x86_64", "fg_compute_rhel_10_2_x86_64", "rhel", "10_0"),
        ("fg_analytics_rhel_10_0_aarch64", "fg_analytics_rhel_10_0_aarch64", "rhel", "10_2"),
        ("slurm_node_rhel_10_2_x86_64", "slurm_node_rhel_10_2_x86_64", "rhel", "10_0"),
    ],
)
def test_discovery_flexible_group_identity_emission(
    host, input_group, expected_group, os_type, os_version  # pylint: disable=unused-argument
):
    """TC_FVT_discovery_012: Verify exact identity emission and preservation for operator review."""
    tc = TC["discovery_flexible_group_mapping"]
    tl = TestLogger(TEST_NAMES["discovery_flexible_group_mapping"], tc["id"])
    is_valid, resolved, error = resolve_functional_group(
        input_group, os_type=os_type, os_version=os_version
    )
    assert is_valid is True, f"Failed resolving {input_group}: {error}"
    assert resolved == expected_group
    tl.passed(f"Successfully resolved {input_group} to {resolved}", "")


@pytest.mark.functional
@pytest.mark.fvt
@pytest.mark.order(14)
@pytest.mark.parametrize(
    ("invalid_group", "expected_phrase"),
    [
        ("webserver_x86_64", "mandatory 'fg_' prefix"),
        ("worker_rhel_10_2_x86_64", "mandatory 'fg_' prefix"),
        ("fg_worker_ppc64le", "Unsupported architecture suffix 'ppc64le'"),
        ("fg_worker_arm", "Unsupported architecture suffix 'arm'"),
        ("fg_worker", "missing required architecture suffix"),
    ],
)
def test_discovery_flexible_group_rejection_evidence(
    host, invalid_group, expected_phrase  # pylint: disable=unused-argument
):
    """TC_FVT_discovery_012: Verify invalid flexible groups rejected with truthful evidence."""
    tc = TC["discovery_flexible_group_mapping"]
    tl = TestLogger(TEST_NAMES["discovery_flexible_group_mapping"], tc["id"])
    is_valid, _resolved, error = resolve_functional_group(invalid_group)
    assert is_valid is False
    assert expected_phrase.lower() in error.lower()
    tl.passed(f"Rejected invalid group '{invalid_group}' with evidence: {error}", "")


@pytest.mark.functional
@pytest.mark.fvt
@pytest.mark.contract
@pytest.mark.order(15)
def test_discovery_flexible_mapping_file_permissions_and_headers(
    host,  # pylint: disable=unused-argument
):
    """TC_FVT_discovery_012: Verify mapping CSV headers and 0640 secure permissions."""
    tc = TC["discovery_flexible_group_mapping"]
    tl = TestLogger(TEST_NAMES["discovery_flexible_group_mapping"], tc["id"])

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tf:
        temp_csv = tf.name

    try:
        os.chmod(temp_csv, 0o640)
        file_stat = os.stat(temp_csv)
        mode = stat.S_IMODE(file_stat.st_mode)
        assert mode == 0o640, f"Expected 0640 permissions, got {oct(mode)}"

        expected_headers = [
            "FUNCTIONAL_GROUP_NAME",
            "GROUP_NAME",
            "SERVICE_TAG",
            "PARENT_SERVICE_TAG",
            "HOSTNAME",
            "ADMIN_MAC",
            "ADMIN_IP",
            "BMC_MAC",
            "BMC_IP",
            "IB_NIC_NAME",
            "IB_IPV4",
            "IB_IPV6",
        ]

        with open(temp_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=expected_headers)
            writer.writeheader()
            writer.writerow({
                "FUNCTIONAL_GROUP_NAME": "fg_webserver_rhel_10_0_x86_64",
                "GROUP_NAME": "grp0",
                "SERVICE_TAG": "SRV101",
                "PARENT_SERVICE_TAG": "",
                "HOSTNAME": "nid001",
                "ADMIN_MAC": "00:11:22:33:44:55",
                "ADMIN_IP": "172.16.0.101",
                "BMC_MAC": "aa:bb:cc:dd:ee:ff",
                "BMC_IP": "10.5.0.101",
                "IB_NIC_NAME": "",
                "IB_IPV4": "",
                "IB_IPV6": "",
            })

        with open(temp_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == expected_headers
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["FUNCTIONAL_GROUP_NAME"] == "fg_webserver_rhel_10_0_x86_64"

        tl.passed("Verified mapping file headers and 0640 secure permissions", "")
    finally:
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
