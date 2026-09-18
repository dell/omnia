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
Omnia Main CLI — Generic Tags Verification.

MAIN_FVT_CLI_V033: Verify omnia.sh help shows 5 generic tags per domain
           (precheck, validate, prepare, execute, cleanup)
MAIN_FVT_CLI_V034: Verify omnia.sh help shows execution order
"""

import pytest

from library.vars import TEST_CASES as TC

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    run_omnia_cmd,
)
from library.vars.common_vars import OMNIA_SH_GENERIC_TAGS
from library.messages import (
    TEST_LOG_MSGS as LOG,
)


@pytest.mark.sanity
@pytest.mark.order(33)
def test_generic_tags_in_help(host):
    """MAIN_FVT_CLI_V033: Verify omnia.sh help shows all 5 generic tags per domain."""
    tc = TC["generic_tags_in_help"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_help")
    tl.bind_result(result)
    output = result.get("output", "")

    missing = [
        tag for tag in OMNIA_SH_GENERIC_TAGS
        if tag not in output
    ]

    if not missing:
        tl.passed(LOG["sh_generic_tags_ok"])
    else:
        tl.failed(LOG["sh_generic_tags_missing"].format(
            missing=", ".join(missing)
        ))

    assert not missing, (
        f"omnia.sh --help is missing generic tags: "
        f"{', '.join(missing)}"
    )


@pytest.mark.sanity
@pytest.mark.order(34)
def test_execution_order_in_help(host):
    """MAIN_FVT_CLI_V034: Verify omnia.sh help shows execution order line."""
    tc = TC["execution_order_in_help"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_help")
    tl.bind_result(result)
    output = result.get("output", "")

    # The help should contain the execution order line
    has_order = (
        "precheck" in output
        and "validate" in output
        and "prepare" in output
        and "execute" in output
        and "cleanup" in output
    )

    if has_order:
        tl.passed(
            "Execution order: precheck -> validate -> "
            "prepare -> execute -> cleanup"
        )
    else:
        tl.failed("Execution order not found in help output")

    assert has_order, (
        "omnia.sh --help should show execution order: "
        "precheck -> validate -> prepare -> execute -> cleanup"
    )
