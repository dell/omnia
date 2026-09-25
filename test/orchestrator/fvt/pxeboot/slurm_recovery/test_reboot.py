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

"""Explicitly authorized full Slurm cluster reboot recovery."""

import pytest
from library.functions import check_slurm_cluster_recovery

from fvt.result import verify_pxeboot


@pytest.mark.disruptive
@pytest.mark.functional
@pytest.mark.reboot
@pytest.mark.slurm
@pytest.mark.order(262)
def test_slurm_cluster_recovery(host):
    """Reboot mapped Slurm nodes and verify scheduler and workload recovery."""
    verify_pxeboot(host, "slurm_recovery", check_slurm_cluster_recovery)
