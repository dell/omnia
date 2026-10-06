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

"""Pytest fixtures for PowerVault iSCSI storage verification."""

import pytest


def pytest_configure(config):
    """Register custom markers for PowerVault tests."""
    config.addinivalue_line(
        "markers", "powervault_infrastructure: iSCSI and multipath infrastructure tests"
    )
    config.addinivalue_line(
        "markers", "powervault_mounts: partition, filesystem, and mount validation"
    )
    config.addinivalue_line(
        "markers", "powervault_binds: bind mount and targeting validation"
    )
    config.addinivalue_line(
        "markers", "powervault_cloudinit: cloud-init and log validation"
    )
