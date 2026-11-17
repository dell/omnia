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

"""Bootstrap token security and TTL contracts after Kubernetes provisioning."""

import pytest
from library.functions import (
    TestLogger,
    check_kubernetes_bootstrap_token_ttl,
    check_kubernetes_cp_join_file_format,
    check_kubernetes_cp_join_file_permissions,
    check_kubernetes_worker_join_file_format,
    check_kubernetes_worker_join_file_permissions,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_pxeboot


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(40809)
def test_kubernetes_worker_join_file_permissions(host):
    """Verify worker-join-command.sh has mode 600 and is owned by root."""
    tc = TC["kubernetes_worker_join_file_permissions"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_worker_join_file_permissions)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(40810)
def test_kubernetes_cp_join_file_permissions(host):
    """Verify control-plane-join-command.sh has mode 600 and is owned by root."""
    tc = TC["kubernetes_cp_join_file_permissions"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_cp_join_file_permissions)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(40811)
def test_kubernetes_worker_join_file_format(host):
    """Verify worker join file is single-line, matches worker regex, rejected by CP regex."""
    tc = TC["kubernetes_worker_join_file_format"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_worker_join_file_format)


@pytest.mark.buildstream
@pytest.mark.sanity
@pytest.mark.kubernetes
@pytest.mark.order(40812)
def test_kubernetes_cp_join_file_format(host):
    """Verify CP join file is single-line, matches CP regex, rejected by worker regex."""
    tc = TC["kubernetes_cp_join_file_format"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_cp_join_file_format)


@pytest.mark.functional
@pytest.mark.buildstream
@pytest.mark.kubernetes
@pytest.mark.order(40813)
def test_kubernetes_bootstrap_token_ttl(host):
    """Run refresh script, extract tokens from join files, verify TTL in kubeadm token list."""
    tc = TC["kubernetes_bootstrap_token_ttl"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_pxeboot(test_log, tc, host, check_kubernetes_bootstrap_token_ttl)
