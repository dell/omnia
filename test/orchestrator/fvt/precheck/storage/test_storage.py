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

"""Configured NFS endpoint reachability contract."""

import pytest
from library.functions import check_precheck_nfs_servers

from fvt.result import verify_precheck


@pytest.mark.sanity
@pytest.mark.order(3)
def test_precheck_nfs_servers(host):
    """Require every mapping-selected NFS server to answer ICMP from the OIM."""
    verify_precheck(host, "precheck_nfs_servers", check_precheck_nfs_servers)
