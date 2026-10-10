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

"""VAST Slurm log persistence validation test."""

import pytest

from fvt.result import verify_pxeboot
from library.functions import check_vast_slurm_logs_persistence


@pytest.mark.sanity
@pytest.mark.order(713)
@pytest.mark.vast_persistence
def test_vast_slurm_logs_persistence(host):
    """Verify Slurm logs on persistent storage; sacct accessible."""
    verify_pxeboot(
        host, "vast_slurm_logs_persistence",
        check_vast_slurm_logs_persistence,
    )
