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
Omnia Main Execution — Run Domain with Tags.

Tests actual execution of ``omnia.sh --run <domain> --tags <tag>``
for each generic tag against image_build_manager.

TC_EX_007: Execute --run image_build_manager --tags precheck
TC_EX_008: Execute --run image_build_manager --tags validate
TC_EX_009: Execute --run image_build_manager --tags prepare
TC_EX_010: Execute --run image_build_manager --tags execute
TC_EX_011: Execute --run image_build_manager --tags cleanup
"""

import pytest

from library.functions import TestLogger
from library.functions.omnia_main_func import run_omnia_cmd
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


DOMAIN = "image_build_manager"


@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(10)
def test_run_precheck(host):
    """TC_EX_007: Execute --run image_build_manager --tags precheck."""
    tl = TestLogger(
        TEST_NAMES["exec_run_precheck"], "TC_EX_007"
    )

    result = run_omnia_cmd(
        host, "omnia_sh_run_domain_tag",
        domain=DOMAIN, tag="precheck",
    )

    if result["success"]:
        tl.passed(LOG["exec_run_ok"].format(
            domain=DOMAIN, tag="precheck",
            rc=result["rc"], duration=result["duration"],
        ))
    else:
        tl.failed(
            LOG["exec_run_failed"].format(
                domain=DOMAIN, tag="precheck",
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_run_failed"].format(
        domain=DOMAIN, tag="precheck", rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(11)
def test_run_validate(host):
    """TC_EX_008: Execute --run image_build_manager --tags validate."""
    tl = TestLogger(
        TEST_NAMES["exec_run_validate"], "TC_EX_008"
    )

    result = run_omnia_cmd(
        host, "omnia_sh_run_domain_tag",
        domain=DOMAIN, tag="validate",
    )

    if result["success"]:
        tl.passed(LOG["exec_run_ok"].format(
            domain=DOMAIN, tag="validate",
            rc=result["rc"], duration=result["duration"],
        ))
    else:
        tl.failed(
            LOG["exec_run_failed"].format(
                domain=DOMAIN, tag="validate",
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_run_failed"].format(
        domain=DOMAIN, tag="validate", rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(12)
def test_run_prepare(host):
    """TC_EX_009: Execute --run image_build_manager --tags prepare."""
    tl = TestLogger(
        TEST_NAMES["exec_run_validate"], "TC_EX_009"
    )

    result = run_omnia_cmd(
        host, "omnia_sh_run_domain_tag",
        domain=DOMAIN, tag="prepare",
    )

    if result["success"]:
        tl.passed(LOG["exec_run_ok"].format(
            domain=DOMAIN, tag="prepare",
            rc=result["rc"], duration=result["duration"],
        ))
    else:
        tl.failed(
            LOG["exec_run_failed"].format(
                domain=DOMAIN, tag="prepare",
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_run_failed"].format(
        domain=DOMAIN, tag="prepare", rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(13)
def test_run_execute(host):
    """TC_EX_010: Execute --run image_build_manager --tags execute."""
    tl = TestLogger(
        TEST_NAMES["exec_run_validate"], "TC_EX_010"
    )

    result = run_omnia_cmd(
        host, "omnia_sh_run_domain_tag",
        domain=DOMAIN, tag="execute",
    )

    if result["success"]:
        tl.passed(LOG["exec_run_ok"].format(
            domain=DOMAIN, tag="execute",
            rc=result["rc"], duration=result["duration"],
        ))
    else:
        tl.failed(
            LOG["exec_run_failed"].format(
                domain=DOMAIN, tag="execute",
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_run_failed"].format(
        domain=DOMAIN, tag="execute", rc=result["rc"],
    )


@pytest.mark.sanity
@pytest.mark.functional
@pytest.mark.order(14)
def test_run_cleanup(host):
    """TC_EX_011: Execute --run image_build_manager --tags cleanup."""
    tl = TestLogger(
        TEST_NAMES["exec_run_validate"], "TC_EX_011"
    )

    result = run_omnia_cmd(
        host, "omnia_sh_run_domain_tag",
        domain=DOMAIN, tag="cleanup",
    )

    if result["success"]:
        tl.passed(LOG["exec_run_ok"].format(
            domain=DOMAIN, tag="cleanup",
            rc=result["rc"], duration=result["duration"],
        ))
    else:
        tl.failed(
            LOG["exec_run_failed"].format(
                domain=DOMAIN, tag="cleanup",
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See output above"),
        )

    assert result["success"], ASSERT["exec_run_failed"].format(
        domain=DOMAIN, tag="cleanup", rc=result["rc"],
    )
