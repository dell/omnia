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

"""Contracts for Kubernetes HA fields on the deployed service_k8s_cluster entry."""

import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker


REPO_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = REPO_ROOT / "src" / "orchestrator"
SOURCE_PLUGIN_ROOT = ORCHESTRATOR_ROOT / "plugins"
if str(SOURCE_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_PLUGIN_ROOT))

from module_utils.orchestrator_validation.validators import (  # noqa: E402
    k8s_ha_validator,
)


def _write_mapping(path, functional_group="research_rhel_10_0_x86_64"):
    path.write_text(
        "FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,"
        "HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IP\n"
        f"{functional_group},group-a,tag-1,,node-1,00:11:22:33:44:55,"
        "192.0.2.10,00:11:22:33:44:66,192.0.2.11,,\n",
        encoding="utf-8",
    )


def test_omnia_schema_types_deployed_cluster_ha_fields():
    """ORCH_UT_100: The schema types HA fields; L2 owns workload-aware presence."""
    schema_path = (
        ORCHESTRATOR_ROOT
        / "plugins/module_utils/orchestrator_validation/schema/omnia_config.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    cluster_schema = {
        "$ref": "#/definitions/serviceK8sCluster",
        "definitions": schema["definitions"],
    }
    validator = Draft7Validator(cluster_schema, format_checker=FormatChecker())
    base = {
        "cluster_name": "service",
        "deployment": True,
        "etcd_on_local_disk": False,
        "k8s_cni": "calico",
        "pod_external_ip_range": "192.0.2.0/24",
        "k8s_service_addresses": "10.96.0.0/12",
        "k8s_pod_network_cidr": "10.244.0.0/16",
        "nfs_storage_name": "nfs",
        "k8s_crio_storage_size": "100G",
    }

    assert not list(validator.iter_errors(base))
    assert not list(validator.iter_errors({**base, "virtual_ip_address": ""}))
    assert list(validator.iter_errors({**base, "enable_k8s_ha": "yes"}))
    assert list(validator.iter_errors({**base, "virtual_ip_address": "bogus"}))
    assert not list(
        validator.iter_errors(
            {**base, "enable_k8s_ha": True, "virtual_ip_address": "192.0.2.20"}
        )
    )


def test_relocated_ha_network_checks_use_the_deployed_cluster(tmp_path):
    """ORCH_UT_101: Merged HA fields retain VIP collision/subnet validation."""
    mapping = tmp_path / "pxe_mapping_file.csv"
    _write_mapping(mapping, "service_kube_control_plane_rhel_10_0_x86_64")
    (tmp_path / "orchestrator_config.yml").write_text(
        "pxe_mapping_file_path: ''\n", encoding="utf-8"
    )
    (tmp_path / "network_spec.yml").write_text(
        "Networks:\n"
        "  - admin_network:\n"
        "      subnet: 192.0.2.0\n"
        "      netmask_bits: '24'\n"
        "      primary_oim_admin_ip: 192.0.2.1\n"
        "      primary_oim_bmc_ip: ''\n"
        "      dynamic_range: 192.0.2.100-192.0.2.150\n"
        "      additional_subnets: []\n",
        encoding="utf-8",
    )
    valid_cluster = {
        "deployment": True,
        "enable_k8s_ha": True,
        "virtual_ip_address": "192.0.2.20",
        "pod_external_ip_range": "192.0.2.30-192.0.2.40",
    }

    assert not k8s_ha_validator.validate_deployed_cluster_ha(
        valid_cluster, str(tmp_path)
    )
    errors = k8s_ha_validator.validate_deployed_cluster_ha(
        {**valid_cluster, "virtual_ip_address": "192.0.2.10"},
        str(tmp_path),
    )
    assert any("ADMIN_IP" in error and "conflicts" in error for error in errors)

    for field_name, cluster in (
        ("enable_k8s_ha", {k: v for k, v in valid_cluster.items() if k != "enable_k8s_ha"}),
        ("virtual_ip_address", {**valid_cluster, "enable_k8s_ha": False, "virtual_ip_address": ""}),
    ):
        errors = k8s_ha_validator.validate_deployed_cluster_ha(cluster, str(tmp_path))
        assert any(field_name in error and "must be set" in error for error in errors)

    _write_mapping(mapping, "slurm_node_rhel_10_0_x86_64")
    assert not k8s_ha_validator.is_applicable(str(tmp_path))
    assert not k8s_ha_validator.validate_deployed_cluster_ha(
        {"deployment": True}, str(tmp_path)
    )
