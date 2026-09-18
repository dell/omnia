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
Omnia Main Setup — Directory Verification.

MAIN_FVT_SETUP_V005: Verify base directories created
MAIN_FVT_SETUP_V006: Verify activate-omnia.sh helper script created
"""

import pytest

from library.vars import TEST_CASES as TC

from library.functions import TestLogger, resolve_runtime_paths
from library.functions.omnia_main_func import (
    check_base_dirs_created,
    check_activate_helper,
)
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(5)
def test_base_dirs_created(host):
    """MAIN_FVT_SETUP_V005: Verify base directories created."""
    tc = TC["base_dirs_created"]
    tl = TestLogger(tc["title"], tc["id"])
    data_path = resolve_runtime_paths(host)["data_path"]
    result = check_base_dirs_created(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["base_dirs_ok"].format(
            count=result["details"].split()[0]
        ), {
            "OMNIA_DATA_PATH": data_path,
            "Directories": result["details"],
        })
    else:
        missing = result.get("missing", [])
        tl.failed_fields(LOG["base_dirs_missing"].format(count=len(missing)), {
            "OMNIA_DATA_PATH": data_path,
            "Missing directories": ", ".join(missing) or "unknown",
        })

    assert result["success"], ASSERT["base_dirs_missing"].format(
        missing_list="\n".join(
            f"\u2551   - {d}" for d in result.get("missing", [])
        ),
    )


@pytest.mark.sanity
@pytest.mark.order(6)
def test_activate_helper(host):
    """MAIN_FVT_SETUP_V006: Verify activate-omnia.sh helper script created."""
    tc = TC["activate_helper"]
    tl = TestLogger(tc["title"], tc["id"])
    data_path = resolve_runtime_paths(host)["data_path"]
    helper_path = f"{data_path}/activate-omnia.sh"

    result = check_activate_helper(host)
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["activate_ok"].format(path=helper_path), {
            "Helper path": helper_path,
            "Status": "present and executable",
        })
    else:
        tl.failed_fields(LOG["activate_missing"].format(path=helper_path), {
            "Helper path": helper_path,
            "Status": result.get("error", "missing or not executable"),
        })

    assert result["success"], ASSERT["base_dirs_missing"].format(
        missing_list=f"\u2551   - {helper_path}",
    )
