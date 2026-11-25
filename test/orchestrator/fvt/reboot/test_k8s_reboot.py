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

"""Ordered Kubernetes cluster reboot: graceful shutdown and sequential power-on."""

import pytest
from library.functions import (
    TestLogger,
    check_k8s_ordered_reboot,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.functional
@pytest.mark.reboot
@pytest.mark.kubernetes
@pytest.mark.order(42361)
def test_k8s_ordered_reboot(host):
    """Shut down all K8s nodes in order and power on with per-group verification."""
    tc = TC["k8s_ordered_reboot"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_k8s_ordered_reboot)
