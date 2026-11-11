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

"""TC-FVT-023 extension: live Slurm traffic path over IPoIB.

Captures live Slurm TCP traffic during a 2-node job and verifies that every
Slurm packet crosses the IB interface in the address family Slurm NodeAddr
uses for the active ib_addr_mode, never the admin Ethernet.
"""

import pytest
from library.functions import (
    TestLogger,
    check_ipoib_slurm_comm_path,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.buildstream
@pytest.mark.ipoib
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42514)
def test_ipoib_slurm_comm_path(host):
    """TC-FVT-023 ext: Slurm traffic uses IPoIB in the NodeAddr family, not Ethernet."""
    tc = TC["ipoib_slurm_comm_path"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_ipoib_slurm_comm_path)
