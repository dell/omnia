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
Omnia CLI — Deploy (help + version baseline).

MAIN_FVT_OMNIA_CLI_E001: Verify omnia-cli help returns usage text
MAIN_FVT_OMNIA_CLI_E002: Verify omnia-cli version shows release info
"""

import pytest

from library.vars import TEST_CASES as TC

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    check_cli_help_output,
    check_cli_version_output,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_cli_help_output(host):
    """MAIN_FVT_OMNIA_CLI_E001: Verify omnia-cli help returns usage text."""
    tc = TC["cli_help_output"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_cli_help_output(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed(LOG["cli_help_ok"])
    else:
        missing = result.get("missing_sections", [])
        tl.failed(LOG["cli_help_missing_section"].format(
            section=", ".join(missing)
        ))

    assert result["success"], ASSERT["cli_help_missing"].format(
        sections=", ".join(
            result.get("missing_sections", [])
        ),
    )


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(1)
def test_cli_version_output(host):
    """MAIN_FVT_OMNIA_CLI_E002: Verify omnia-cli version shows release info."""
    tc = TC["cli_version_output"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_cli_version_output(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed(LOG["cli_version_ok"].format(
            version=result["details"]
        ))
    else:
        tl.failed(LOG["cli_version_missing"])

    assert result["success"], ASSERT["cli_version_missing"]
