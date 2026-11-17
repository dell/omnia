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

"""TC-FVT-020: Slurm NodeAddr idempotent reapplication across a provision rerun."""

import pytest
from library.functions import TestLogger, check_ipoib_nodeaddr_reapply
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.ipoib
@pytest.mark.slurm
@pytest.mark.reprovision
@pytest.mark.order(42611)
def test_ipoib_nodeaddr_reapply(host):
    """TC-FVT-020: NodeAddr values are unchanged and unique after provision reruns."""
    tc = TC["ipoib_nodeaddr_reapply"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_ipoib_nodeaddr_reapply)
