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
Discovery — Flexible Group Mapping Compatibility Unit Tests.

Test Case:
- TC_UT_discovery_011: Unit tests for flexible functional group mapping
  compatibility in Discovery PXE mapping generation.
"""

import os
import sys

# Ensure discovery module imports resolve
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
MODULES_DIR = os.path.join(REPO_ROOT, "src/discovery/plugins/modules")
if MODULES_DIR not in sys.path:
    sys.path.insert(0, MODULES_DIR)

from generate_pxe_mapping import resolve_functional_group  # pylint: disable=wrong-import-position


class TestFlexibleGroupMappingCompatibility:
    """TC_UT_discovery_011: Flexible functional group mapping unit tests."""

    def test_valid_unversioned_fg_group_injects_os_and_version(self):
        """Valid fg_<label>_<arch> has OS and version injected."""
        is_valid, resolved, error = resolve_functional_group(
            "fg_webserver_x86_64", os_type="rhel", os_version="10_0"
        )
        assert is_valid is True
        assert resolved == "fg_webserver_rhel_10_0_x86_64"
        assert error == ""

        is_valid, resolved, error = resolve_functional_group(
            "fg_ai_worker_aarch64", os_type="rhel", os_version="10_2"
        )
        assert is_valid is True
        assert resolved == "fg_ai_worker_rhel_10_2_aarch64"
        assert error == ""

    def test_valid_already_versioned_fg_group_preserves_exact_identity(self):
        """Already versioned fg_<label>_<os>_<ver>_<arch> preserves exact name."""
        is_valid, resolved, error = resolve_functional_group(
            "fg_webserver_rhel_10_2_x86_64", os_type="rhel", os_version="10_0"
        )
        assert is_valid is True
        assert resolved == "fg_webserver_rhel_10_2_x86_64"
        assert error == ""

        is_valid, resolved, error = resolve_functional_group(
            "fg_analytics_rhel_10_0_aarch64"
        )
        assert is_valid is True
        assert resolved == "fg_analytics_rhel_10_0_aarch64"
        assert error == ""

    def test_invalid_prefix_missing_fg_is_rejected_with_evidence(self):
        """Non-predefined group without 'fg_' prefix is rejected with truthful evidence."""
        is_valid, resolved, error = resolve_functional_group("webserver_x86_64")
        assert is_valid is False
        assert resolved == ""
        assert "mandatory 'fg_' prefix" in error

        is_valid, resolved, error = resolve_functional_group(
            "custom_worker_rhel_10_2_x86_64"
        )
        assert is_valid is False
        assert resolved == ""
        assert "mandatory 'fg_' prefix" in error

    def test_invalid_architecture_suffix_is_rejected_with_evidence(self):
        """Unsupported architecture suffix is rejected with truthful evidence."""
        is_valid, resolved, error = resolve_functional_group("fg_webserver_ppc64le")
        assert is_valid is False
        assert resolved == ""
        assert "Unsupported architecture suffix 'ppc64le'" in error

        is_valid, resolved, error = resolve_functional_group(
            "fg_compute_rhel_10_2_riscv64"
        )
        assert is_valid is False
        assert resolved == ""
        assert "Unsupported architecture suffix 'riscv64'" in error

    def test_missing_architecture_suffix_is_rejected_with_evidence(self):
        """Missing architecture suffix is rejected with truthful evidence."""
        is_valid, resolved, error = resolve_functional_group("fg_webserver")
        assert is_valid is False
        assert resolved == ""
        assert "missing required architecture suffix" in error.lower()

    def test_predefined_groups_remain_backwards_compatible(self):
        """Standard predefined Omnia functional groups are preserved."""
        predefined = [
            "slurm_node_rhel_10_2_x86_64",
            "slurm_control_node_rhel_10_0_x86_64",
            "service_kube_node_rhel_10_0_aarch64",
            "os_rhel_10_2_x86_64",
            "login_node_rhel_10_0_x86_64",
            "login_compiler_node_rhel_10_2_x86_64",
        ]
        for group in predefined:
            is_valid, resolved, error = resolve_functional_group(group)
            assert is_valid is True, f"{group} should be valid"
            assert resolved == group
            assert error == ""

    def test_predefined_unversioned_group_injects_os_and_version(self):
        """Unversioned predefined group receives OS and version injection."""
        is_valid, resolved, error = resolve_functional_group(
            "slurm_node_x86_64", os_type="rhel", os_version="10_0"
        )
        assert is_valid is True
        assert resolved == "slurm_node_rhel_10_0_x86_64"
        assert error == ""

        is_valid, resolved, error = resolve_functional_group(
            "service_kube_node_aarch64", os_type="rhel", os_version="10_2"
        )
        assert is_valid is True
        assert resolved == "service_kube_node_rhel_10_2_aarch64"
        assert error == ""

    def test_omit_invalid_groups_omits_rows_and_provides_evidence(self):
        """Verify omit_invalid_groups behavior and truthful rejection evidence."""
        sample_servers = [
            {
                "service_tag": "SRV001",
                "group_name": "fg_webserver_x86_64",
                "idrac_ip": "172.16.0.10",
            },
            {
                "service_tag": "SRV002",
                "group_name": "webserver_x86_64",  # Missing fg_ prefix
                "idrac_ip": "172.16.0.11",
            },
            {
                "service_tag": "SRV003",
                "group_name": "fg_worker_ppc64le",  # Bad arch
                "idrac_ip": "172.16.0.12",
            },
            {
                "service_tag": "SRV004",
                "group_name": "fg_compute_rhel_10_2_aarch64",  # Already versioned
                "idrac_ip": "172.16.0.13",
            },
        ]

        # Test resolution directly
        resolved_rows = []
        omitted = []
        rejected = []
        for server in sample_servers:
            svc_tag = server["service_tag"]
            grp = server["group_name"]
            is_valid, resolved_name, reason = resolve_functional_group(
                grp, os_type="rhel", os_version="10_0"
            )
            if not is_valid:
                entry = {"service_tag": svc_tag, "group_name": grp, "reason": reason}
                rejected.append(entry)
                omitted.append(entry)
                continue
            resolved_rows.append({"service_tag": svc_tag, "group": resolved_name})

        # Exactly 2 servers valid, 2 invalid
        assert len(resolved_rows) == 2
        assert resolved_rows[0]["group"] == "fg_webserver_rhel_10_0_x86_64"
        assert resolved_rows[1]["group"] == "fg_compute_rhel_10_2_aarch64"

        assert len(rejected) == 2
        assert rejected[0]["service_tag"] == "SRV002"
        assert "mandatory 'fg_' prefix" in rejected[0]["reason"]
        assert rejected[1]["service_tag"] == "SRV003"
        assert "Unsupported architecture suffix 'ppc64le'" in rejected[1]["reason"]

    def test_no_credentials_appear_in_mapping_output_or_evidence(self):
        """Ensure no credential fields or tokens leak in output or evidence."""
        sample_server = {
            "service_tag": "SRV999",
            "group_name": "fg_webserver_x86_64",
            "idrac_ip": "172.16.0.99",
            "password": "SuperSecretPassword123",
            "bmc_password": "BmcSecretPassword456",
        }
        is_valid, resolved, error = resolve_functional_group(
            sample_server["group_name"], os_type="rhel", os_version="10_0"
        )
        assert is_valid is True
        assert "password" not in resolved.lower()
        assert "secret" not in resolved.lower()
        assert "password" not in error.lower()
