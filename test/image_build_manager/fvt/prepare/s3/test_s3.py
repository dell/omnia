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
Image Build Prepare — S3 Bucket Verification.

TC_PR_004: Verify S3 buckets created after prepare
"""

import pytest

from library.functions import TestLogger, check_s3_buckets
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(7)
def test_s3_buckets_after_prepare(host):
    """TC_PR_008: Verify S3 buckets created after prepare."""
    tl = TestLogger(TEST_NAMES["s3_buckets_created"], "TC_PR_008")
    result = check_s3_buckets(host)

    if result["success"]:
        tl.passed(
            LOG["s3_buckets_ok"].format(count=len(result["found"])),
            result["details"],
        )
    else:
        tl.failed(
            LOG["s3_buckets_missing"].format(
                count=len(result["missing"])
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["s3_buckets_missing"].format(
        missing_list="\n".join(
            f"\u2551   - {b}" for b in result["missing"]
        ),
    )
