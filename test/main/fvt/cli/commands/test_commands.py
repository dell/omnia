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
Omnia Main CLI — Command Verification.

TC_CL_002: Verify omnia.sh with no args shows help
TC_CL_003: Verify --run with invalid domain exits with error
TC_CL_004: Verify --run without domain exits with error
TC_CL_005: Verify --validate without domain exits with error
TC_CL_006: Verify unknown option exits with error
"""

import pytest

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    run_omnia_cmd,
    run_omnia_cmd_expect_error,
    check_error_contains,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_no_args_shows_help(host):
    """TC_CL_002: Verify omnia.sh with no args shows help."""
    tl = TestLogger(
        TEST_NAMES["no_args_shows_help"], "TC_CL_002"
    )
    result = run_omnia_cmd(host, "omnia_sh_no_args")
    output = result["output"]

    has_usage = check_error_contains(output, "usage")

    if has_usage:
        tl.passed(LOG["help_ok"])
    else:
        tl.failed(LOG["help_missing_section"].format(
            section="USAGE"
        ))

    assert has_usage, ASSERT["help_missing"].format(
        sections="USAGE",
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_run_invalid_domain(host):
    """TC_CL_003: Verify --run with invalid domain exits with error."""
    tl = TestLogger(
        TEST_NAMES["invalid_domain_error"], "TC_CL_003"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_run_invalid",
        domain="nonexistent_domain_xyz",
    )

    if result["success"]:
        tl.passed(LOG["error_exit_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["error_not_raised"].format(
        command="omnia.sh --run nonexistent_domain_xyz",
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_run_no_domain(host):
    """TC_CL_004: Verify --run without domain exits with error."""
    tl = TestLogger(
        TEST_NAMES["run_no_domain_error"], "TC_CL_004"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_run_no_domain",
    )

    if result["success"]:
        tl.passed(LOG["error_exit_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["error_not_raised"].format(
        command="omnia.sh --run",
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_validate_no_domain(host):
    """TC_CL_005: Verify --validate without domain exits with error."""
    tl = TestLogger(
        TEST_NAMES["validate_no_domain_error"], "TC_CL_005"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_validate_no_domain",
    )

    if result["success"]:
        tl.passed(LOG["error_exit_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["error_not_raised"].format(
        command="omnia.sh --validate",
        rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_unknown_option(host):
    """TC_CL_006: Verify unknown option exits with error."""
    tl = TestLogger(
        TEST_NAMES["unknown_option_error"], "TC_CL_006"
    )
    result = run_omnia_cmd_expect_error(
        host, "omnia_sh_unknown_option",
    )

    if result["success"]:
        tl.passed(LOG["error_exit_ok"].format(
            rc=result["rc"]
        ))
    else:
        tl.failed(LOG["error_exit_unexpected"].format(
            rc=result["rc"]
        ))

    assert result["success"], ASSERT["error_not_raised"].format(
        command="omnia.sh --bogus",
        rc=result["rc"],
    )
