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

TC_SU_007: Verify base directories created
TC_SU_008: Verify activate-omnia.sh helper script created
"""

import pytest

from library.functions import TestLogger, load_test_config
from library.functions.omnia_main_func import (
    check_base_dirs_created,
    check_activate_helper,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(6)
def test_base_dirs_created(host):
    """TC_SU_007: Verify base directories created."""
    tl = TestLogger(
        TEST_NAMES["base_dirs_created"], "TC_SU_007"
    )
    result = check_base_dirs_created(host)

    if result["success"]:
        tl.passed(LOG["base_dirs_ok"].format(
            count=result["details"].split()[0]
        ))
    else:
        missing = result.get("missing", [])
        tl.failed(LOG["base_dirs_missing"].format(
            count=len(missing)
        ))

    assert result["success"], ASSERT["base_dirs_missing"].format(
        missing_list="\n".join(
            f"\u2551   - {d}" for d in result.get("missing", [])
        ),
    )


@pytest.mark.sanity
@pytest.mark.order(7)
def test_activate_helper(host):
    """TC_SU_008: Verify activate-omnia.sh helper script created."""
    tl = TestLogger(
        TEST_NAMES["activate_helper"], "TC_SU_008"
    )
    config = load_test_config()
    data_path = config.get(
        "omnia_data_path", "/opt/omnia"
    )
    helper_path = f"{data_path}/activate-omnia.sh"

    result = check_activate_helper(host)

    if result["success"]:
        tl.passed(LOG["activate_ok"].format(
            path=helper_path
        ))
    else:
        tl.failed(LOG["activate_missing"].format(
            path=helper_path
        ))

    assert result["success"], ASSERT["base_dirs_missing"].format(
        missing_list=f"\u2551   - {helper_path}",
    )
