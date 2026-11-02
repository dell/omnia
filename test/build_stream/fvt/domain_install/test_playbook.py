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
Domain Install — Initialization.

Runs ``./omnia.sh --setup-venv`` from ``src/main`` (no timeout): it creates or
updates the shared venv, then runs every domain's ``domain-init.sh`` for
build_stream, repo_manager, image_build_manager and orchestrator, which installs
dependencies, creates log directories and copies the input files to
``<OMNIA_DATA_PATH>/<domain>/input/<project>``. A read-only precheck runs first;
when it fails, the setup is skipped (see conftest.py). The ``initialization``
suite verifies the result. No domain cleanup removes the setup.
"""

import pytest

from library.functions import (
    TestLogger,
    failure_summary,
    load_test_config,
    precheck_domain_install,
    run_omnia_sh,
)
from library.functions.config_func import omnia_setup_arguments
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC
from library.vars.common_vars import INIT_DOMAINS


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(5000)
def test_precheck_domain_install(host):
    """Check omnia.sh and the domain initializers before --setup-venv (read-only)."""
    tc = TC["precheck_domain_install"]
    tl = TestLogger(tc["title"], tc["id"])
    result = precheck_domain_install(host)
    if result["success"]:
        tl.passed_fields(LOG["domain_install_precheck_ok"], result["fields"])
    else:
        tl.failed_fields(LOG["domain_install_precheck_failed"].format(
            count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["domain_install_precheck_failed"].format(
        failures=failure_summary(result))


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(5001)
def test_deploy_domain_install(host):
    """Run ./omnia.sh --setup-venv and require a zero exit code."""
    del host
    tc = TC["deploy_domain_install"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_omnia_sh(omnia_setup_arguments(load_test_config()))
    fields = [
        ("Command", result["command"]),
        ("Domains initialized", ", ".join(INIT_DOMAINS)),
        ("Return code", result["rc"]),
        ("Duration seconds", f"{result['duration']:.1f}"),
    ]
    if result["success"]:
        tl.passed_fields(LOG["domain_install_ok"].format(duration=result["duration"]), fields)
    else:
        tl.failed_fields(
            LOG["domain_install_failed"].format(rc=result["rc"], duration=result["duration"]),
            [*fields, ("Error", result.get("error") or "See output above")])
    assert result["success"], ASSERT["domain_install_failed"].format(
        rc=result["rc"], duration=result["duration"], error=result.get("error"))
