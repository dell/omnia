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

"""Generator-specific pytest fixtures."""

import pytest
from typing import Dict, Any, List


@pytest.fixture
def sample_pxe_rows() -> List[Dict[str, str]]:
    """Two valid PXE mapping rows with all mandatory fields."""
    return [
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
        },
        {
            "FUNCTIONAL_GROUP_NAME": "slurm_node_x86_64",
            "GROUP_NAME": "group1",
            "SERVICE_TAG": "SVC002",
            "PARENT_SERVICE_TAG": "",
            "HOSTNAME": "node02",
            "ADMIN_MAC": "AA:BB:CC:DD:EE:03",
            "ADMIN_IP": "10.0.0.11",
            "BMC_MAC": "AA:BB:CC:DD:EE:04",
            "BMC_IP": "10.0.1.11",
            "IB_NIC_NAME": "",
            "IB_IP": "",
        },
    ]


@pytest.fixture
def sample_admin_inventory_rows() -> List[Dict[str, str]]:
    """Two valid admin inventory rows."""
    return [
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
    ]


@pytest.fixture
def sample_network_data() -> List[Dict[str, Any]]:
    """Valid Networks list with admin subnet."""
    return [
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
    ]


@pytest.fixture
def sample_storage_data() -> Dict[str, Any]:
    """Mounts, swap, and powervault entries for storage tests."""
    return {
        "mounts": [
            {
                "name": "/home",
                "functional_group_prefix": "slurm_node",
                "groups": "group1",
                "node_mount_point": "/home",
            }
        ],
        "swap": [
            {
                "filename": "/swapfile",
                "functional_group_prefix": "slurm_node",
                "size": "auto",
                "maxsize": "2G",
            }
        ],
        "powervault_config": [
            {
                "name": "pv1",
                "functional_group_prefix": "slurm_node",
                "node_mount_point": "/data",
                "ip": "192.168.1.100",
            }
        ],
    }


@pytest.fixture
def sample_cloud_init_data() -> Dict[str, Any]:
    """Common runcmd + groups with group_name for cloud init tests."""
    return {
        "cloud_init_common": {
            "runcmd": [
                {"command": "echo hello"},
                {"command": "echo world"},
            ],
        },
        "cloud_init_groups": [
            {
                "group_name": "compute",
                "write_files": [
                    {"path": "/etc/test.conf", "content": "key=value"},
                ],
                "runcmd": [
                    {"command": "systemctl restart test"},
                ],
            },
        ],
    }
