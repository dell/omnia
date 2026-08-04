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
from library.messages import TEST_NAMES, LOG_MSGS, ASSERT_MSGS


@pytest.mark.sanity
@pytest.mark.order(4)
def test_repo_status_success(host):
    """TC_DL_005: Verify repo_status.yml reports success."""
    tl = TestLogger(TEST_NAMES["repo_status_success"], "TC_DL_005")
    result = check_repo_status_file(host)

    if result["success"]:
        tl.passed(LOG_MSGS["repo_status_ok"], result["details"])
    else:
        tl.failed(LOG_MSGS["repo_status_failed"], result.get("error", ""))

    assert result["success"], ASSERT_MSGS["repo_status_failed"].format(
        error=result.get("error", ""),
        status_path=result.get("status_path", ""),
    )
