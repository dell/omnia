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
    check_slurm_infiniband_configuration,
    check_slurm_infiniband_connectivity,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.sanity,
    pytest.mark.slurm,
    pytest.mark.non_disruptive,
]


@pytest.mark.order(260)
def test_slurm_infiniband_configuration(host):
    """Verify mapped IB interface, address, prefix, link, MTU, and OFED."""
    verify_pxeboot(host, "slurm_ib_configuration", check_slurm_infiniband_configuration)


@pytest.mark.order(261)
def test_slurm_infiniband_connectivity(host):
    """Verify every mapped IB endpoint can reach every mapped peer."""
    verify_pxeboot(host, "slurm_ib_connectivity", check_slurm_infiniband_connectivity)
