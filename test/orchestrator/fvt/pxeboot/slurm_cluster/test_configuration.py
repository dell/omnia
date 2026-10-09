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

"""Slurm configuration source, distribution, and configless contracts."""

import pytest
from library.functions import (
    TestLogger,
    check_slurm_custom_configuration,
    check_slurm_reconfigure,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.non_disruptive
@pytest.mark.functional
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.order(41107)
def test_slurm_reconfigure(host):
    """Reconfigure Slurm and verify membership remains healthy."""
    tc = TC["slurm_reconfigure"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_reconfigure)


@pytest.mark.non_disruptive
@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.order(41109)
def test_slurm_custom_configuration(host):
    """Verify custom values, NFS delivery, and effective visibility."""
    tc = TC["slurm_custom_configuration"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_slurm_custom_configuration)
