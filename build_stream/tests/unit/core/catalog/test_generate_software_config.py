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

"""Unit tests for generate_software_config function."""

import json
import os
import tempfile

import pytest

from core.catalog.adapter_policy import generate_software_config
from core.catalog import adapter_policy_schema_consts as schema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_output(output_dir: str) -> dict:
    """Read generated software_config.json from output_dir/input/."""
    path = os.path.join(output_dir, "input", "software_config.json")
    assert os.path.isfile(path), f"Expected file not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _software_by_name(result: dict, name: str) -> dict:
    """Find a software entry by name in the softwares list."""
    matches = [s for s in result["softwares"] if s["name"] == name]
    assert len(matches) == 1, f"Expected exactly 1 entry for '{name}', got {len(matches)}"
    return matches[0]


# ---------------------------------------------------------------------------
# Static fields
# ---------------------------------------------------------------------------

class TestStaticFields:
    """Tests for static / catalog-derived fields."""

    def test_cluster_os_type_from_os_family(self, tmp_path: str) -> None:
        configs = {"x86_64": {"pkg.json": {"pkg": {schema.CLUSTER: [{"package": "a"}]}}}}
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        result = _read_output(str(tmp_path))
        assert result["cluster_os_type"] == "rhel"

    def test_cluster_os_version_from_os_version(self, tmp_path: str) -> None:
        configs = {"x86_64": {"pkg.json": {"pkg": {schema.CLUSTER: [{"package": "a"}]}}}}
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        result = _read_output(str(tmp_path))
        assert result["cluster_os_version"] == "10.0"

    def test_repo_config_is_partial(self, tmp_path: str) -> None:
        configs = {"x86_64": {"pkg.json": {"pkg": {schema.CLUSTER: [{"package": "a"}]}}}}
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        result = _read_output(str(tmp_path))
        assert result["repo_config"] == "partial"


# ---------------------------------------------------------------------------
# Softwares list — basic
# ---------------------------------------------------------------------------

class TestSoftwaresList:
    """Tests for the softwares list generation."""

    def test_single_arch_single_target(self, tmp_path: str) -> None:
        configs = {
            "x86_64": {
                "openldap.json": {
                    "openldap": {schema.CLUSTER: [{"package": "openldap-clients"}]}
                }
            }
        }
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        result = _read_output(str(tmp_path))
        entry = _software_by_name(result, "openldap")
        assert entry["arch"] == ["x86_64"]
        assert "version" not in entry

    def test_multi_arch_both_non_empty(self, tmp_path: str) -> None:
        configs = {
            "x86_64": {"openldap.json": {"openldap": {schema.CLUSTER: [{"package": "a"}]}}},
            "aarch64": {"openldap.json": {"openldap": {schema.CLUSTER: [{"package": "b"}]}}},
        }
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        entry = _software_by_name(_read_output(str(tmp_path)), "openldap")
        assert "x86_64" in entry["arch"]
        assert "aarch64" in entry["arch"]

    def test_target_name_derived_from_filename(self, tmp_path: str) -> None:
        configs = {
            "x86_64": {"my_custom.json": {"my_custom": {schema.CLUSTER: [{"package": "x"}]}}}
        }
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        names = [s["name"] for s in _read_output(str(tmp_path))["softwares"]]
        assert "my_custom" in names


# ---------------------------------------------------------------------------
# Arch exclusion when all subgroups empty
# ---------------------------------------------------------------------------

class TestArchExclusion:
    """Tests for excluding arches with all-empty cluster arrays."""

    def test_excludes_arch_when_all_subgroups_empty(self, tmp_path: str) -> None:
        configs = {
            "x86_64": {"csi_driver_powerscale.json": {
                "csi_driver_powerscale": {schema.CLUSTER: [{"package": "csi-powerscale"}]}
            }},
            "aarch64": {"csi_driver_powerscale.json": {
                "csi_driver_powerscale": {schema.CLUSTER: []}
            }},
        }
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        entry = _software_by_name(_read_output(str(tmp_path)), "csi_driver_powerscale")
        assert entry["arch"] == ["x86_64"]

    def test_excludes_target_entirely_when_empty_on_all_arches(self, tmp_path: str) -> None:
        configs = {
            "x86_64": {"csi_driver_powerscale.json": {
                "csi_driver_powerscale": {schema.CLUSTER: []}
            }},
            "aarch64": {"csi_driver_powerscale.json": {
                "csi_driver_powerscale": {schema.CLUSTER: []}
            }},
        }
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        names = [s["name"] for s in _read_output(str(tmp_path))["softwares"]]
        assert "csi_driver_powerscale" not in names

    def test_target_missing_from_arch_excluded(self, tmp_path: str) -> None:
        configs = {
            "x86_64": {"service_k8s.json": {
                "service_kube_control_plane": {schema.CLUSTER: [{"package": "kubectl"}]},
                "service_k8s": {schema.CLUSTER: [{"package": "kubeadm"}]},
            }},
            "aarch64": {},
        }
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        entry = _software_by_name(_read_output(str(tmp_path)), "service_k8s")
        assert entry["arch"] == ["x86_64"]


# ---------------------------------------------------------------------------
# Version strings
# ---------------------------------------------------------------------------

class TestVersionStrings:
    """Tests for static version injection."""

    def test_service_k8s_gets_version(self, tmp_path: str) -> None:
        configs = {"x86_64": {"service_k8s.json": {
            "service_kube_control_plane": {schema.CLUSTER: [{"package": "kubectl"}]},
            "service_k8s": {schema.CLUSTER: [{"package": "kubeadm"}]},
        }}}
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        entry = _software_by_name(_read_output(str(tmp_path)), "service_k8s")
        assert entry["version"] == "1.34.1"

    def test_csi_target_gets_version(self, tmp_path: str) -> None:
        configs = {"x86_64": {"csi_driver_powerscale.json": {
            "csi_driver_powerscale": {schema.CLUSTER: [{"package": "csi-powerscale"}]}
        }}}
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        entry = _software_by_name(_read_output(str(tmp_path)), "csi_driver_powerscale")
        assert entry["version"] == "v2.15.0"

    def test_regular_target_has_no_version(self, tmp_path: str) -> None:
        configs = {"x86_64": {"openldap.json": {
            "openldap": {schema.CLUSTER: [{"package": "openldap-clients"}]}
        }}}
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        entry = _software_by_name(_read_output(str(tmp_path)), "openldap")
        assert "version" not in entry


# ---------------------------------------------------------------------------
# Subgroup sections
# ---------------------------------------------------------------------------

class TestSubgroupSections:
    """Tests for subgroup (role) sections in the output."""

    def test_lists_non_empty_subgroups(self, tmp_path: str) -> None:
        configs = {"x86_64": {"slurm_custom.json": {
            "slurm_control_node": {schema.CLUSTER: [{"package": "slurmctld"}]},
            "slurm_node": {schema.CLUSTER: [{"package": "slurmd"}]},
            "login_node": {schema.CLUSTER: [{"package": "slurm"}]},
            "slurm_custom": {schema.CLUSTER: [{"package": "munge"}]},
        }}}
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        result = _read_output(str(tmp_path))
        assert "slurm_custom" in result
        sub_names = {e["name"] for e in result["slurm_custom"]}
        assert sub_names == {"slurm_control_node", "slurm_node", "login_node"}

    def test_target_name_not_in_subgroups(self, tmp_path: str) -> None:
        configs = {"x86_64": {"slurm_custom.json": {
            "slurm_control_node": {schema.CLUSTER: [{"package": "slurmctld"}]},
            "slurm_custom": {schema.CLUSTER: [{"package": "munge"}]},
        }}}
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        sub_names = {e["name"] for e in _read_output(str(tmp_path))["slurm_custom"]}
        assert "slurm_custom" not in sub_names

    def test_excludes_empty_cluster_subgroups(self, tmp_path: str) -> None:
        configs = {"x86_64": {"service_k8s.json": {
            "service_kube_control_plane": {schema.CLUSTER: [{"package": "kubectl"}]},
            "service_kube_node": {schema.CLUSTER: []},
            "service_k8s": {schema.CLUSTER: [{"package": "kubeadm"}]},
        }}}
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        sub_names = {e["name"] for e in _read_output(str(tmp_path))["service_k8s"]}
        assert "service_kube_control_plane" in sub_names
        assert "service_kube_node" not in sub_names

    def test_no_subgroup_section_for_single_role_target(self, tmp_path: str) -> None:
        configs = {"x86_64": {"openldap.json": {
            "openldap": {schema.CLUSTER: [{"package": "openldap-clients"}]}
        }}}
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        result = _read_output(str(tmp_path))
        assert "openldap" not in result

    def test_subgroups_merged_across_arches(self, tmp_path: str) -> None:
        configs = {
            "x86_64": {"slurm_custom.json": {
                "slurm_control_node": {schema.CLUSTER: [{"package": "slurmctld"}]},
                "slurm_node": {schema.CLUSTER: [{"package": "slurmd"}]},
                "slurm_custom": {schema.CLUSTER: [{"package": "munge"}]},
            }},
            "aarch64": {"slurm_custom.json": {
                "slurm_node": {schema.CLUSTER: [{"package": "slurmd"}]},
                "login_node": {schema.CLUSTER: [{"package": "slurm"}]},
                "slurm_custom": {schema.CLUSTER: [{"package": "munge"}]},
            }},
        }
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        sub_names = {e["name"] for e in _read_output(str(tmp_path))["slurm_custom"]}
        assert sub_names == {"slurm_control_node", "slurm_node", "login_node"}


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_all_arch_configs(self, tmp_path: str) -> None:
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs={},
        )
        result = _read_output(str(tmp_path))
        assert result["softwares"] == []
        assert result["cluster_os_type"] == "rhel"
        assert result["cluster_os_version"] == "10.0"
        assert result["repo_config"] == "partial"

    def test_creates_output_directory(self, tmp_path: str) -> None:
        output_dir = os.path.join(str(tmp_path), "deep", "nested", "output")
        configs = {"x86_64": {"pkg.json": {"pkg": {schema.CLUSTER: [{"package": "a"}]}}}}
        generate_software_config(
            output_dir=output_dir, os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        path = os.path.join(output_dir, "input", "software_config.json")
        assert os.path.isfile(path)


# ---------------------------------------------------------------------------
# Realistic scenario
# ---------------------------------------------------------------------------

class TestRealisticScenario:
    """End-to-end-style test matching real project_default/software_config.json."""

    def test_realistic_multi_target(self, tmp_path: str) -> None:
        configs = {
            "x86_64": {
                "default_packages.json": {
                    "default_packages": {schema.CLUSTER: [{"package": "systemd"}]}
                },
                "slurm_custom.json": {
                    "slurm_control_node": {schema.CLUSTER: [{"package": "slurmctld"}]},
                    "slurm_node": {schema.CLUSTER: [{"package": "slurmd"}]},
                    "login_node": {schema.CLUSTER: [{"package": "slurm"}]},
                    "login_compiler_node": {schema.CLUSTER: [{"package": "slurmd"}]},
                    "slurm_custom": {schema.CLUSTER: [{"package": "munge"}]},
                },
                "service_k8s.json": {
                    "service_kube_control_plane_first": {schema.CLUSTER: [{"package": "kubeadm"}]},
                    "service_kube_control_plane": {schema.CLUSTER: [{"package": "kubectl"}]},
                    "service_kube_node": {schema.CLUSTER: [{"package": "kubelet"}]},
                    "service_k8s": {schema.CLUSTER: [{"package": "cri-o"}]},
                },
                "csi_driver_powerscale.json": {
                    "csi_driver_powerscale": {schema.CLUSTER: [{"package": "csi-powerscale"}]}
                },
            },
            "aarch64": {
                "default_packages.json": {
                    "default_packages": {schema.CLUSTER: [{"package": "systemd"}]}
                },
                "slurm_custom.json": {
                    "slurm_control_node": {schema.CLUSTER: [{"package": "slurmctld"}]},
                    "slurm_node": {schema.CLUSTER: [{"package": "slurmd"}]},
                    "login_node": {schema.CLUSTER: [{"package": "slurm"}]},
                    "login_compiler_node": {schema.CLUSTER: [{"package": "slurmd"}]},
                    "slurm_custom": {schema.CLUSTER: [{"package": "munge"}]},
                },
                "service_k8s.json": {
                    "service_kube_control_plane_first": {schema.CLUSTER: []},
                    "service_kube_control_plane": {schema.CLUSTER: []},
                    "service_kube_node": {schema.CLUSTER: []},
                    "service_k8s": {schema.CLUSTER: [{"package": "firewalld"}]},
                },
                "csi_driver_powerscale.json": {
                    "csi_driver_powerscale": {schema.CLUSTER: []}
                },
            },
        }
        generate_software_config(
            output_dir=str(tmp_path), os_family="rhel", os_version="10.0",
            all_arch_target_configs=configs,
        )
        result = _read_output(str(tmp_path))

        # default_packages: both arches
        dp = _software_by_name(result, "default_packages")
        assert "x86_64" in dp["arch"]
        assert "aarch64" in dp["arch"]
        assert "version" not in dp

        # slurm_custom: both arches
        sc = _software_by_name(result, "slurm_custom")
        assert "x86_64" in sc["arch"]
        assert "aarch64" in sc["arch"]

        # service_k8s: both arches (aarch64 service_k8s itself has packages)
        k8s = _software_by_name(result, "service_k8s")
        assert "x86_64" in k8s["arch"]
        assert "aarch64" in k8s["arch"]
        assert k8s["version"] == "1.34.1"

        # csi_driver_powerscale: x86_64 only
        csi = _software_by_name(result, "csi_driver_powerscale")
        assert csi["arch"] == ["x86_64"]
        assert csi["version"] == "v2.15.0"

        # slurm_custom subgroups
        assert "slurm_custom" in result
        sc_subs = {e["name"] for e in result["slurm_custom"]}
        assert sc_subs == {"slurm_control_node", "slurm_node", "login_node", "login_compiler_node"}

        # service_k8s subgroups (only non-empty ones across all arches)
        assert "service_k8s" in result
        k8s_subs = {e["name"] for e in result["service_k8s"]}
        assert "service_kube_control_plane_first" in k8s_subs
        assert "service_kube_control_plane" in k8s_subs
        assert "service_kube_node" in k8s_subs
