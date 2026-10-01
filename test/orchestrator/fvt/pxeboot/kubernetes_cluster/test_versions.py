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

"""Kubernetes configured-version and runtime-compatibility contracts."""

import pytest
from library.functions import (
    check_kubernetes_configured_versions,
    check_kubernetes_version_compatibility,
)

from fvt.result import verify_pxeboot


@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(207)
def test_kubernetes_version_compatibility(host):
    """Verify Kubernetes, kubeadm, and CRI-O version alignment."""
    verify_pxeboot(host, "kubernetes_versions", check_kubernetes_version_compatibility)


@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(208)
def test_kubernetes_configured_versions(host):
    """Verify deployed component versions against the selected catalog."""
    verify_pxeboot(
        host,
        "kubernetes_configured_versions",
        check_kubernetes_configured_versions,
    )
