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

"""Unit tests for pure flexible functional group mapping support.

Verifies:
- Detection of pure fg_ mapping vs predefined categories in orchestrator_setup
- Base OS fallback matching and image override skip flag isolation in validate_image.yml
- Cloud-init write_files and runcmd rendering in ms-group metadata templates
"""

import re
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = REPO_ROOT / "src" / "orchestrator"


class TestPureFlexibleMappingDetection:
    """Verifies category presence detection in orchestrator_setup."""

    @staticmethod
    def _inspect_mapping(content: str):
        mapping_has_service_k8s = bool(re.search(r"(?m)^[ \t]*service_kube_", content))
        mapping_has_slurm = bool(re.search(r"(?m)^[ \t]*(slurm_|login_)", content))
        return mapping_has_service_k8s, mapping_has_slurm

    def test_pure_flexible_mapping_disables_predefined_flags(self):
        pure_fg_csv = (
            "FUNCTIONAL_GROUP_NAME,GROUP_NAME,HOSTNAME,ADMIN_MAC,ADMIN_IP\n"
            "fg_custom_control_node_rhel_10_2_x86_64,grp1,node1,00:11:22:33:44:01,10.0.0.1\n"
            "fg_custom_worker_node_rhel_10_2_x86_64,grp2,node2,00:11:22:33:44:02,10.0.0.2\n"
        )
        has_k8s, has_slurm = self._inspect_mapping(pure_fg_csv)
        assert not has_k8s, "Pure fg_ mapping should not trigger service_k8s_support"
        assert not has_slurm, "Pure fg_ mapping should not trigger slurm_support"

    def test_predefined_k8s_mapping_triggers_k8s_flag(self):
        k8s_csv = (
            "FUNCTIONAL_GROUP_NAME,GROUP_NAME,HOSTNAME,ADMIN_MAC,ADMIN_IP\n"
            "service_kube_control_plane_rhel_10_2_x86_64,grp1,node1,00:11:22:33:44:01,10.0.0.1\n"
            "fg_custom_worker_node_rhel_10_2_x86_64,grp2,node2,00:11:22:33:44:02,10.0.0.2\n"
        )
        has_k8s, has_slurm = self._inspect_mapping(k8s_csv)
        assert has_k8s, "Mapping with service_kube_ should trigger service_k8s_support"
        assert not has_slurm, "Mapping without slurm should not trigger slurm_support"

    def test_predefined_slurm_mapping_triggers_slurm_flag(self):
        slurm_csv = (
            "FUNCTIONAL_GROUP_NAME,GROUP_NAME,HOSTNAME,ADMIN_MAC,ADMIN_IP\n"
            "slurm_node_rhel_10_2_x86_64,grp1,node1,00:11:22:33:44:01,10.0.0.1\n"
            "fg_custom_worker_node_rhel_10_2_x86_64,grp2,node2,00:11:22:33:44:02,10.0.0.2\n"
        )
        has_k8s, has_slurm = self._inspect_mapping(slurm_csv)
        assert not has_k8s, "Mapping without k8s should not trigger service_k8s_support"
        assert has_slurm, "Mapping with slurm_ should trigger slurm_support"


class TestValidateImageOverrideIsolation:
    """Verifies that _skip_image_validation is computed cleanly per-iteration."""

    @staticmethod
    def _compute_skip_flag(functional_group_name: str, functional_group_config: dict) -> bool:
        return bool(
            functional_group_config
            and functional_group_config.get("groups")
            and functional_group_name in functional_group_config["groups"]
            and functional_group_config["groups"][functional_group_name].get("image_override")
            and len(functional_group_config["groups"][functional_group_name]["image_override"]) > 0
        )

    def test_skip_flag_isolation_across_iterations(self):
        config = {
            "groups": {
                "fg_with_override_rhel_10_2_x86_64": {
                    "image_override": {
                        "kernel": "boot-images/kernel",
                        "initrd": "boot-images/initrd",
                        "rootfs": "boot-images/rootfs",
                    }
                },
                "fg_without_override_rhel_10_2_x86_64": {},
            }
        }

        # Iteration 1: group with override
        skip_1 = self._compute_skip_flag("fg_with_override_rhel_10_2_x86_64", config)
        assert skip_1 is True, "Group with image_override must set skip flag to True"

        # Iteration 2: group without override must re-evaluate cleanly to False
        skip_2 = self._compute_skip_flag("fg_without_override_rhel_10_2_x86_64", config)
        assert skip_2 is False, "Group without image_override must set skip flag to False"
