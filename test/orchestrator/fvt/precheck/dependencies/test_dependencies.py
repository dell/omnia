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

"""Image Builder and Repo Manager status-file contracts."""

import pytest
from library.functions import (
    TestLogger,
    check_precheck_dependencies,
    check_precheck_repositories,
    check_precheck_s3_artifacts,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_precheck


@pytest.mark.sanity
@pytest.mark.order(10401)
def test_precheck_dependencies(host):
    """Require both configured/default dependency outputs to be usable."""
    tc = TC["precheck_dependencies"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_precheck_dependencies)


@pytest.mark.sanity
@pytest.mark.order(10402)
def test_precheck_s3_artifacts(host):
    """Require every kernel, initrd, and rootfs artifact to be reachable."""
    tc = TC["precheck_s3_artifacts"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_precheck_s3_artifacts)


@pytest.mark.sanity
@pytest.mark.order(10403)
def test_precheck_repositories(host):
    """Require every published RPM and file repository to be reachable."""
    tc = TC["precheck_repositories"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_precheck_repositories)
