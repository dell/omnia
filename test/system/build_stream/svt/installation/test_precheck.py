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
Installation — Precheck (exec, runs before build_stream.yml).

Proves, before BuildStream is installed, that build_stream.yml can run
unattended and that the pipelines that follow have what they need:
  installation.catalog resolves to a valid catalog; CATALOG_FILE_PATH valid
  build_stream_config.yml and the BuildStream credential store exist
  pxe_mapping_file.csv has at least two node rows (deploy pipeline swap)
  build_stream.yml --tags precheck passes (repo_manager and
  image_build_manager are ready for BuildStream)
A failure skips the rest of the installation scenario.
"""

import pytest

from library.functions import (
    TestLogger,
    failure_summary,
    installation_settings,
    load_test_config,
    precheck_installation,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC

_SCENARIO = "installation"


@pytest.mark.svt
@pytest.mark.br_86010
@pytest.mark.installation
@pytest.mark.deploy
@pytest.mark.precheck
@pytest.mark.sanity
@pytest.mark.order(2001)
def test_precheck_installation(host):
    """Check the catalog, BuildStream inputs and product precheck before installing."""
    tc = TC["precheck_installation"]
    tl = TestLogger(tc["title"], tc["id"])
    result = precheck_installation(host, installation_settings(load_test_config()))

    if result["success"]:
        tl.passed_fields(LOG["precheck_ok"].format(scenario=_SCENARIO), result["fields"])
    else:
        tl.failed_fields(LOG["precheck_failed"].format(
            scenario=_SCENARIO, count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["precheck_installation_failed"].format(
        failures=failure_summary(result))
