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
Omnia Main CLI — Deploy (placeholder).

MAIN_FVT_CLI_E001: Verify omnia.sh --help returns usage text.

The CLI scenario does not have a traditional "deploy" step.
This test validates that the help output is complete and
serves as the @deploy marker entry point for run_validation.sh.
"""

import pytest

from library.vars import TEST_CASES as TC

from library.functions import TestLogger
from library.functions.omnia_main_func import check_help_output
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_help_output(host):
    """MAIN_FVT_CLI_E001: Verify omnia.sh --help returns usage text."""
    tc = TC["help_output"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_help_output(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed(LOG["help_ok"])
    else:
        missing = result.get("missing_sections", [])
        tl.failed(LOG["help_missing_section"].format(
            section=", ".join(missing)
        ))

    assert result["success"], ASSERT["help_missing"].format(
        sections=", ".join(
            result.get("missing_sections", [])
        ),
    )
