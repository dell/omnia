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

"""Slurm InfiniBand configuration and peer-connectivity contracts."""

import pytest
from library.functions import (
    TestLogger,
    check_slurm_infiniband_configuration,
    check_slurm_infiniband_connectivity,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41801)
def test_slurm_infiniband_configuration(host):
    """Verify mapped IB interface, address, prefix, link, MTU, and OFED."""
    tc = TC["slurm_ib_configuration"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_infiniband_configuration)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(41802)
def test_slurm_infiniband_connectivity(host):
    """Verify every mapped IB endpoint can reach every mapped peer."""
    tc = TC["slurm_ib_connectivity"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_infiniband_connectivity)
