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

"""Shared pytest fixtures for GUI module tests."""

import pytest
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Create a temporary output directory."""
    out = tmp_path / "out"
    out.mkdir()
    return out


@pytest.fixture
def noop_write_yaml():
    """No-op callback matching the write_yaml_fn generator interface."""
    def _noop(path, data):
        pass
    return _noop


@pytest.fixture
def noop_ensure_directory():
    """No-op callback matching the ensure_directory_fn generator interface."""
    def _noop(path):
        pass
    return _noop


@pytest.fixture
def sample_wizard_data() -> Dict[str, Any]:
    """Minimal valid wizard payload with Networks, PXE mapping, and cluster config."""
    return {
        "Networks": [
            {
                "admin_network": {
                    "oim_nic_name": "eno1",
                    "subnet": "10.0.0.0",
                    "netmask_bits": "24",
                    "primary_oim_admin_ip": "10.0.0.1",
                    "primary_oim_bmc_ip": "10.0.1.1",
                    "dynamic_range": "10.0.0.100-10.0.0.200",
                    "dns": ["10.0.0.2"],
                    "ntp_servers": [{"address": "10.0.0.3", "type": "server"}],
                },
            }
        ],
        "pxe_mapping_data": [
            {
                "FUNCTIONAL_GROUP_NAME": "slurm_node_x86_64",
                "GROUP_NAME": "group1",
                "SERVICE_TAG": "SVC001",
                "PARENT_SERVICE_TAG": "",
                "HOSTNAME": "node01",
                "ADMIN_MAC": "AA:BB:CC:DD:EE:01",
                "ADMIN_IP": "10.0.0.10",
                "BMC_MAC": "AA:BB:CC:DD:EE:02",
                "BMC_IP": "10.0.1.10",
                "IB_NIC_NAME": "",
                "IB_IP": "",
            }
        ],
        "slurm_cluster": [
            {"cluster_name": "test_cluster", "partition": "normal"}
        ],
        "enable_bmc_discovery": False,
        "ome_ip": "",
    }


@pytest.fixture
def sample_magellan_data() -> Dict[str, Any]:
    """Wizard data for Magellan discovery flow."""
    return {
        "enable_bmc_discovery": False,
        "admin_inventory_path": "/opt/omnia/input/project_default/admin_inventory.csv",
        "admin_inventory_data": [
            {
                "SERVICE_TAG": "SVC001",
                "GROUP_NAME": "group1",
                "FUNCTIONAL_GROUP_NAME": "compute",
                "ROW": "R1",
                "RACK": "A1",
                "SLOT": "1",
                "RANGE": "",
            },
            {
                "SERVICE_TAG": "SVC002",
                "GROUP_NAME": "group2",
                "FUNCTIONAL_GROUP_NAME": "storage",
                "ROW": "",
                "RACK": "",
                "SLOT": "",
                "RANGE": "",
            },
        ],
        "Networks": [
            {
                "admin_network": {
                    "oim_nic_name": "eno1",
                    "subnet": "10.0.0.0",
                    "netmask_bits": "24",
                    "primary_oim_admin_ip": "10.0.0.1",
                    "primary_oim_bmc_ip": "10.0.1.1",
                    "dynamic_range": "10.0.0.100-10.0.0.200",
                    "dns": ["10.0.0.2"],
                    "ntp_servers": [{"address": "10.0.0.3", "type": "server"}],
                },
            }
        ],
    }
