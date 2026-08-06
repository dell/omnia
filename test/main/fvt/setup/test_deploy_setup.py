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
Omnia Main Setup — Deploy.

TC_SU_001: Deploy omnia.sh --setup-venv --deps-only
"""

import pytest

from library.functions import TestLogger
from library.functions.omnia_main_func import run_omnia_cmd
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_setup_venv(host):
    """TC_SU_001: Deploy omnia.sh --setup-venv --deps-only."""
    tl = TestLogger(
        TEST_NAMES["deploy_setup_venv"], "TC_SU_001"
    )
    result = run_omnia_cmd(host, "omnia_sh_setup_venv")

    if result["success"]:
        tl.passed(LOG["setup_success"].format(
            duration=result["duration"]
        ))
    else:
        tl.failed(
            LOG["setup_failed"].format(
                rc=result["rc"],
                duration=result["duration"],
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["setup_failed"].format(
        rc=result["rc"],
        duration=result["duration"],
    )
