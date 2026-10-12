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

from library.functions import (
    TestLogger,
    check_vast_slurm_logs_persistence,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.sanity
@pytest.mark.vast_persistence
@pytest.mark.order(42114)
def test_vast_slurm_logs_persistence(host):
    """Verify Slurm logs on persistent storage; sacct accessible."""
    tc = TC["vast_slurm_logs_persistence"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_vast_slurm_logs_persistence)
