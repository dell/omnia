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

"""Omnia Main extended init execution and postcondition verification."""

import pytest

from library.functions import TestLogger
from library.functions.omnia_main_func import (
    check_domain_input_staged,
    check_domain_log_dirs,
    run_omnia_cmd,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT
from library.messages import TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

DOMAIN = "image_build_manager"


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(1)
def test_deploy_init_domain(host):
    """Run extended init for the Image Build Manager domain."""
    tc = TC["deploy_init_domain"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_cmd(host, "omnia_sh_init_domain", domain=DOMAIN)
    tl.bind_result(result)
    if result["success"]:
        tl.passed(LOG["exec_init_domain_ok"].format(
            domain=DOMAIN, rc=result["rc"], duration=result["duration"]
        ))
    else:
        tl.failed(LOG["exec_init_domain_failed"].format(
            domain=DOMAIN, rc=result["rc"], duration=result["duration"]
        ))
    assert result["success"], ASSERT["exec_init_domain_failed"].format(
        domain=DOMAIN, rc=result["rc"]
    )


@pytest.mark.functional
@pytest.mark.order(9)
def test_verify_domain_log_dirs(host):
    """Verify extended init created the Image Build Manager log directory."""
    tc = TC["verify_domain_log_dirs"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_domain_log_dirs(host, domains=[DOMAIN])
    tl.bind_result(result)
    if result["success"]:
        tl.passed(LOG["log_dirs_ok"].format(count=len(result.get("found", []))))
    else:
        tl.failed(LOG["log_dirs_missing"].format(
            count=len(result.get("missing", []))
        ))
    assert result["success"], ASSERT["log_dirs_missing"].format(
        missing=", ".join(result.get("missing", []))
    )


@pytest.mark.functional
@pytest.mark.order(10)
def test_verify_domain_input_staged(host):
    """Verify extended init staged Image Build Manager inputs."""
    tc = TC["verify_domain_input_staged"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_domain_input_staged(host, domain=DOMAIN)
    tl.bind_result(result)
    if result["success"]:
        tl.passed(LOG["input_staged_ok"].format(
            domain=DOMAIN, count=result.get("file_count", 0)
        ))
    else:
        tl.failed(LOG["input_not_staged"].format(domain=DOMAIN))
    assert result["success"], ASSERT["input_not_staged"].format(domain=DOMAIN)
