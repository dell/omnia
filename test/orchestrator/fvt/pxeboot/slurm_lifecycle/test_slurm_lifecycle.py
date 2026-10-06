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

"""Slurm node remove/add lifecycle verification.

Exercises the standard Slurm compute node removal and re-addition
lifecycle.  Only existing ``slurm_node_*`` entries from the PXE mapping
can be used.  You cannot add a new node that is not already present in
the PXE mapping; the test removes existing nodes and then adds the same
nodes back.
"""

import pytest
from library.functions import (
    check_slurm_node_add,
    check_slurm_node_remove,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.slurm,
    pytest.mark.functional,
    pytest.mark.disruptive,
]


@pytest.mark.order(290)
def test_slurm_node_remove(host):
    """Remove Slurm compute node(s) from PXE mapping, provision, verify."""
    verify_pxeboot(host, "slurm_node_remove", check_slurm_node_remove)


@pytest.mark.order(291)
def test_slurm_node_add(host):
    """Restore removed node(s) to PXE mapping, provision, verify re-addition."""
    verify_pxeboot(host, "slurm_node_add", check_slurm_node_add)
