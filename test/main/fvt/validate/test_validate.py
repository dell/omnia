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

"""Execute the Image Build Manager validate phase through omnia.sh."""

import pytest

from library.functions import TestLogger
from library.functions.omnia_main_func import run_omnia_cmd
from library.messages import TEST_ASSERT_MSGS as ASSERT
from library.messages import TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

DOMAIN = "image_build_manager"
TAG = "validate"


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(0)
def test_deploy_run_validate(host):
    """Execute the validate tag through the Main entry point."""
    tc = TC["deploy_run_validate"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(
        host, "omnia_sh_run_domain_tag", domain=DOMAIN, tag=TAG
    )
    tl.bind_result(result)
    if result["success"]:
        tl.passed(LOG["exec_run_ok"].format(
            domain=DOMAIN, tag=TAG,
            rc=result["rc"], duration=result["duration"]
        ))
    else:
        tl.failed(LOG["exec_run_failed"].format(
            domain=DOMAIN, tag=TAG,
            rc=result["rc"], duration=result["duration"]
        ))
    assert result["success"], ASSERT["exec_run_failed"].format(
        domain=DOMAIN, tag=TAG, rc=result["rc"]
    )
