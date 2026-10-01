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
    check_precheck_dependencies,
    check_precheck_repositories,
    check_precheck_s3_artifacts,
)

from fvt.result import verify_precheck


@pytest.mark.sanity
@pytest.mark.order(4)
def test_precheck_dependencies(host):
    """Require both configured/default dependency outputs to be usable."""
    verify_precheck(host, "precheck_dependencies", check_precheck_dependencies)


@pytest.mark.sanity
@pytest.mark.order(6)
def test_precheck_s3_artifacts(host):
    """Require every kernel, initrd, and rootfs artifact to be reachable."""
    verify_precheck(host, "precheck_s3_artifacts", check_precheck_s3_artifacts)


@pytest.mark.sanity
@pytest.mark.order(7)
def test_precheck_repositories(host):
    """Require every published RPM and file repository to be reachable."""
    verify_precheck(host, "precheck_repositories", check_precheck_repositories)
