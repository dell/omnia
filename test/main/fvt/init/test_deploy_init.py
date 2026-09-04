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
Omnia Main Init — Deploy.

MAIN_FVT_INIT_E001: Deploy omnia.sh --init
"""

import pytest

from library.vars import TEST_CASES as TC

from library.functions import TestLogger
from library.functions.omnia_main_func import resolve_runtime_paths, run_omnia_cmd
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_init(host):
    """MAIN_FVT_INIT_E001: Deploy omnia.sh --init."""
    tc = TC["deploy_init"]
    tl = TestLogger(tc["title"], tc["id"])
    runtime = resolve_runtime_paths(host)
    result = run_omnia_cmd(host, "omnia_sh_init")
    tl.bind_result(result)

    if result["success"]:
        tl.passed_fields(LOG["init_success"].format(
            duration=result["duration"]
        ), {
            "Command": "omnia.sh --init",
            "Project": runtime["project_name"],
            "OMNIA_DATA_PATH": runtime["data_path"],
            "Return code": result["rc"],
            "Duration": f"{result['duration']:.1f}s",
        })
    else:
        tl.failed_fields(LOG["init_failed"].format(
            rc=result["rc"], duration=result["duration"]
        ), {
            "Command": "omnia.sh --init",
            "Return code": result["rc"],
            "Error": result.get("error", "See command output"),
        })

    assert result["success"], ASSERT["init_failed"].format(
        rc=result["rc"],
        duration=result["duration"],
    )
