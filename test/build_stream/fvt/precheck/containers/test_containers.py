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

"""
Precheck Containers — prerequisite containers.

pulp (repo_manager), minio-server and registry (image_build_manager)
must be running, as build_stream.yml --tags precheck requires.
"""

import pytest

from library.functions import (
    TestLogger,
    check_precheck_containers,
    report_check,
)
from library.vars import TEST_CASES as TC
from library.messages import TEST_ASSERT_MSGS as ASSERT


@pytest.mark.sanity
@pytest.mark.order(20201)
def test_precheck_containers(host):
    """Verify the prerequisite containers are running."""
    tc = TC["precheck_containers"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_precheck_containers(host)
    report_check(tl, result)
    assert result["success"], ASSERT["precheck_failed"].format(
        component="prerequisite containers", error=result["error"],
    )
