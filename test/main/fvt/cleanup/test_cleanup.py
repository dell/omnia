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

"""Execute explicit Omnia cleanup without including it in regular runs."""

import pytest

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    is_running_from_omnia_venv,
    run_omnia_cmd,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT
from library.messages import TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

_SKIP_VENV_MSG = (
    "Skipped: running from omnia production venv — "
    "cannot destroy the active interpreter"
)


@pytest.mark.deploy
@pytest.mark.cleanup
@pytest.mark.order(0)
def test_deploy_cleanup(host):
    """Run omnia.sh cleanup only when explicitly selected."""
    tc = TC["deploy_cleanup"]
    tl = TestLogger(tc["title"], tc["id"])
    if is_running_from_omnia_venv(host):
        tl.passed(_SKIP_VENV_MSG)
        pytest.skip(_SKIP_VENV_MSG)

    result = run_omnia_cmd(host, "omnia_sh_cleanup_yes")
    tl.bind_result(result)
    if result["success"]:
        tl.passed(LOG["exec_cleanup_ok"].format(rc=result["rc"]))
    else:
        tl.failed(LOG["exec_cleanup_failed"].format(rc=result["rc"]))
    assert result["success"], ASSERT["exec_cleanup_failed"].format(rc=result["rc"])
