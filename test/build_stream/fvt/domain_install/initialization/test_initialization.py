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
Domain Install — Setup and Domain Initialization Verification.

Validates what ./omnia.sh --setup-venv left on the OIM, one test case each:
  main                 /etc/omnia/omnia.env and its values, the shared venv,
                       activate-omnia.sh
  repo_manager         every src/<domain>/input file staged in
  image_build_manager  <data>/input/<project>; <data>/{input,output,log}/<project>
  orchestrator         and /var/log/omnia/<domain> exist
  build_stream         the same, plus the application copy matches src/build_stream/app
Every checked item is listed with a check or cross mark.
"""

import pytest

from library.functions import (
    TestLogger,
    failure_summary,
    verify_domain_initialized,
    verify_main_setup,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC


def _check_domain(host, domain: str) -> None:
    """Verify one domain initializer and assert the result."""
    tc = TC[f"{domain}_initialized"]
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_domain_initialized(host, domain)
    if result["success"]:
        tl.passed_fields(LOG["domain_initialized_ok"].format(
            domain=domain, count=len(result["fields"])), result["fields"])
    else:
        tl.failed_fields(LOG["domain_initialized_failed"].format(
            domain=domain, count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["domain_initialized_failed"].format(
        domain=domain, failures=failure_summary(result))


@pytest.mark.sanity
@pytest.mark.order(5101)
def test_main_setup_ready(host):
    """Verify the shared setup: omnia.env, the venv and the activation script."""
    tc = TC["main_setup_ready"]
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_main_setup(host)
    if result["success"]:
        tl.passed_fields(LOG["main_setup_ok"].format(count=len(result["fields"])),
                         result["fields"])
    else:
        tl.failed_fields(LOG["main_setup_failed"].format(count=len(result["failures"])),
                         result["fields"])
    assert result["success"], ASSERT["main_setup_failed"].format(
        failures=failure_summary(result))


@pytest.mark.sanity
@pytest.mark.order(5102)
def test_repo_manager_initialized(host):
    """Verify repo_manager input files and directories."""
    _check_domain(host, "repo_manager")


@pytest.mark.sanity
@pytest.mark.order(5103)
def test_image_build_manager_initialized(host):
    """Verify image_build_manager input files and directories."""
    _check_domain(host, "image_build_manager")


@pytest.mark.sanity
@pytest.mark.order(5104)
def test_orchestrator_initialized(host):
    """Verify orchestrator input files and directories."""
    _check_domain(host, "orchestrator")


@pytest.mark.sanity
@pytest.mark.order(5105)
def test_build_stream_initialized(host):
    """Verify build_stream input files, directories and the application copy."""
    _check_domain(host, "build_stream")
