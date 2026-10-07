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

"""HPC benchmarks end-to-end provisioning composite (non-disruptive).

The adjacent-flow invariance checks (TC-14 through TC-17) execute
``pull_benchmarks.sh`` and therefore live in ``test_destructive.py``
behind the ``--run-destructive`` gate.
"""

import pytest
from library.functions import (
    TestLogger,
    check_hpc_benchmarks_e2e_provisioning,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot

@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(42011)
def test_hpc_benchmarks_e2e_provisioning(host):
    """TC-09: Verify the end-to-end benchmark provisioning pipeline."""
    tc = TC["hpc_benchmarks_e2e_provisioning"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_hpc_benchmarks_e2e_provisioning)
