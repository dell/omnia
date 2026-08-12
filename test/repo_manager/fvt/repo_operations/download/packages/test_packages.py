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
Repo Operations — Download — Package Verification Tests.

Validates package download status:
  TC_DL_005: Verify repo_status.yml reports success
"""

import pytest

from library.functions import (
    TestLogger,
    check_repo_status_file,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(4)
def test_repo_status_success(host):
    """TC_DL_005: Verify repo_status.yml reports success."""
    tc = TC["dl_repo_status_success"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_repo_status_file(host)

    if result["success"]:
        tl.passed(LOG["repo_status_ok"], result["details"])
    else:
        tl.failed(LOG["repo_status_failed"], result.get("error", ""))

    assert result["success"], ASSERT["repo_status_failed"].format(
        error=result.get("error", ""),
        status_path=result.get("status_path", ""),
    )
