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
Prepare Base — Precheck (exec, runs before ./omnia.sh --prepare-base).

Proves, without changing the OIM, that --prepare-base can run unattended:
  omnia.env sets OMNIA_DATA_PATH, OMNIA_PROJECT_NAME and OMNIA_VENV_PATH
  the shared venv and src/main/omnia.sh exist
  repo_manager, image_build_manager and orchestrator credential stores
  (file and vault key) exist, so no domain prompts for credentials
A failure skips the rest of the prepare_base scenario.
"""

import pytest

from library.functions import (
    TestLogger,
    failure_summary,
    installation_settings,
    load_test_config,
    precheck_prepare_base,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

_SCENARIO = "prepare_base"


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.prepare_base
@pytest.mark.deploy
@pytest.mark.precheck
@pytest.mark.sanity
@pytest.mark.order(1001)
def test_precheck_prepare_base(host):
    """Check the environment and base domain credentials before --prepare-base."""
    tc = TC["precheck_prepare_base"]
    tl = TestLogger(tc["title"], tc["id"])
    settings = installation_settings(load_test_config())
    result = precheck_prepare_base(host, catalog_selection=settings["catalog"])

    if result["success"]:
        tl.passed_fields(LOG["precheck_ok"].format(scenario=_SCENARIO), result["fields"])
    else:
        tl.failed_fields(LOG["precheck_failed"].format(
            scenario=_SCENARIO, count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["precheck_prepare_base_failed"].format(
        failures=failure_summary(result))
