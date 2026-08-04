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
Omnia CLI — Error Handling Verification.

TC_OC_011: Verify omnia-cli unknown command exits with error
"""

import pytest

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    run_omnia_cli_expect_error,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(10)
def test_cli_unknown_command(host):
    """TC_OC_011: Verify omnia-cli unknown command exits with error."""
    tl = TestLogger(
        TEST_NAMES["cli_unknown_command"], "TC_OC_011"
    )
    result = run_omnia_cli_expect_error(
        host, "omnia_cli_unknown"
    )

    if result["success"]:
        tl.passed(LOG["cli_unknown_error_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(
            "omnia-cli unknown command did not exit"
            f" with error (rc={result['rc']})"
        )

    assert result["success"], ASSERT["error_not_raised"].format(
        command="omnia-cli nonexistent_cmd",
        rc=result["rc"],
    )
