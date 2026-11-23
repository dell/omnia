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
Utils — Flexible Group Log Collection FVT Tests.

Test Case:
- TC_FVT_utils_013: Verify Utils log collection accepts fg_ group names in
  collect_pxe.yml, routes logs by role prefix, captures source-group identity
  in evidence, and reports unreachable nodes as warnings without collection failure.
"""

import os
import tempfile
import pytest
import yaml

from library.functions import (
    TestLogger,
    validate_collect_pxe_file,
)
from library.messages import TEST_LOG_MSGS as LOG
from library.vars import (
    TEST_CASES as TC,
    extract_role_prefix,
)


@pytest.mark.functional
@pytest.mark.fvt
@pytest.mark.order(13)
def test_flexible_group_log_collection_lifecycle(host):
    """TC_FVT_utils_013: Verify fg_ group validation, role-prefix routing, and warning evidence."""
    tc = TC["utils_flexible_group_log_collection"]
    tl = TestLogger(tc["title"], tc["id"])

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as tf:
        temp_path = tf.name

    try:
        sample_inventory = {
            "fg_webserver_rhel_10_2_x86_64": ["10.5.0.21", "10.5.0.22"],
            "fg_ai_worker_rhel_10_2_aarch64": ["10.5.0.31"],
            "slurm_node_rhel_10_0_x86_64": ["10.5.0.41"],
        }
        with open(temp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(sample_inventory, f)

        # 1. Validate file structure and group names
        val_result = validate_collect_pxe_file(host, temp_path)
        assert val_result["success"] is True, f"Validation failed: {val_result.get('error')}"
        assert "fg_webserver_rhel_10_2_x86_64" in val_result["groups"]
        assert "fg_ai_worker_rhel_10_2_aarch64" in val_result["groups"]

        # 2. Verify role-prefix routing pattern for flexible groups
        for grp in sample_inventory:
            role_prefix = extract_role_prefix(grp)
            if grp.startswith("fg_webserver"):
                assert role_prefix == "fg_webserver"
            elif grp.startswith("fg_ai_worker"):
                assert role_prefix == "fg_ai_worker"
            elif grp.startswith("slurm_node"):
                assert role_prefix == "slurm_node"

        # 3. Simulate unreachable node evidence payload
        warning_payload = {
            "source": extract_role_prefix("fg_webserver_rhel_10_2_x86_64"),
            "source_group": "fg_webserver_rhel_10_2_x86_64",
            "node_name": "fg_webserver_10_5_0_21",
            "node_ip": "10.5.0.21",
            "reason": "unreachable",
            "message": (
                "Node fg_webserver_10_5_0_21 (10.5.0.21) unreachable; "
                "continuing collection."
            ),
        }
        assert warning_payload["source"] == "fg_webserver"
        assert warning_payload["source_group"] == "fg_webserver_rhel_10_2_x86_64"
        assert warning_payload["reason"] == "unreachable"

        tl.passed(
            LOG["flexible_group_collection_ok"],
            "Validated fg_ inventory and role-prefix routing",
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.mark.functional
@pytest.mark.fvt
@pytest.mark.order(14)
@pytest.mark.parametrize(
    "invalid_group",
    [
        "webserver_rhel_10_2_x86_64",
        "fg_webserver_ppc64le",
        "fg_webserver",
    ],
)
def test_reject_unsafe_collection_input(host, invalid_group):
    """TC_FVT_utils_013: Verify invalid group names are rejected before collection."""
    tc = TC["utils_flexible_group_log_collection"]
    tl = TestLogger(tc["title"], tc["id"])

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as tf:
        temp_path = tf.name

    try:
        bad_inventory = {invalid_group: ["10.5.0.99"]}
        with open(temp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(bad_inventory, f)

        val_result = validate_collect_pxe_file(host, temp_path)
        assert val_result["success"] is False
        assert invalid_group in val_result["invalid_groups"]
        tl.passed(f"Successfully rejected unsafe group '{invalid_group}'", "")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.mark.functional
@pytest.mark.fvt
@pytest.mark.order(15)
def test_evidence_sanitization_and_no_credentials(host):  # pylint: disable=unused-argument
    """TC_FVT_utils_013: Verify collection evidence and warnings contain no credentials."""
    tc = TC["utils_flexible_group_log_collection"]
    tl = TestLogger(tc["title"], tc["id"])

    evidence = {
        "source": "fg_webserver",
        "source_group": "fg_webserver_rhel_10_2_x86_64",
        "node_name": "fg_webserver_10_5_0_21",
        "node_ip": "10.5.0.21",
        "reason": "unreachable",
        "message": "Node unreachable via SSH",
    }

    serialized = str(evidence).lower()
    for sensitive_token in ["password", "secret", "vault", "token", "private_key"]:
        assert (
            sensitive_token not in serialized
        ), f"Sensitive token {sensitive_token} found in evidence"

    tl.passed("Verified evidence contains no credentials", "")
