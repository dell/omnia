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
Image Build Validate — repo_ssl_verify Configuration Verification.

TC_VL_004: Verify repo_ssl_verify is configured in image_build_config.yml
TC_BD_016: Verify repo_ssl_verify is applied in build templates
"""

import pytest

from library.functions import (
    TestLogger,
    check_repo_ssl_verify_config,
    check_repo_ssl_verify_applied,
)
from library.vars import TEST_CASES as TC
from library.messages import TEST_LOG_MSGS as LOG


@pytest.mark.sanity
@pytest.mark.order(3)
def test_repo_ssl_verify_config(host):
    """TC_VL_004: Verify repo_ssl_verify is configured."""
    tc = TC["repo_ssl_verify_config"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_repo_ssl_verify_config(host)

    if result["success"]:
        tl.passed(LOG["repo_ssl_verify_ok"].format(
            value=result["ssl_verify"]
        ), result["details"])
    else:
        tl.failed(LOG["repo_ssl_verify_missing"], result["details"])

    assert result["success"], result["details"]


@pytest.mark.x86_64
@pytest.mark.functional
@pytest.mark.order(4)
def test_repo_ssl_verify_applied(host):
    """TC_BD_016: Verify repo_ssl_verify is applied in build templates."""
    tc = TC["repo_ssl_verify_applied"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_repo_ssl_verify_applied(host, arch="x86_64")

    if result["success"]:
        tl.passed(
            LOG["repo_ssl_verify_applied_ok"],
            result["details"],
        )
    else:
        failed = [
            r for r in result.get("results", [])
            if not r.get("has_ssl_ref")
        ]
        tl.failed(
            LOG["repo_ssl_verify_not_applied"].format(
                count=len(failed)
            ),
            result["details"],
        )

    assert result["success"], result["details"]
