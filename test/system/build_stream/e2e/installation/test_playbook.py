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
Installation — Deploy BuildStream with the Selected Catalog (exec entry point).

Reads CATALOG_FILE_PATH from /etc/omnia/omnia.env, installs the catalog
selected by installation.catalog (a ./omnia.sh --list-catalogs number or a
full path) there, backing up a different active catalog, and runs
build_stream.yml (no timeout). The result is verified by the health and
repository suites (verify phase).
"""

import pytest

from library.functions import (
    TestLogger,
    failure_summary,
    installation_settings,
    load_test_config,
    run_build_stream_installation,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.installation
@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(2002)
def test_build_stream_installation(host):
    """Place the selected catalog and run build_stream.yml."""
    tc = TC["build_stream_installation"]
    tl = TestLogger(tc["title"], tc["id"])
    settings = installation_settings(load_test_config())
    tl.check(LOG["installation_start"].format(catalog=settings["catalog"]))

    result = run_build_stream_installation(host, settings, tl.info)

    if result["success"]:
        tl.passed_fields(LOG["installation_ok"], result["fields"])
    else:
        tl.failed_fields(
            LOG["installation_failed"].format(count=len(result["failures"])),
            [*result["fields"], *(("Failure", item) for item in result["failures"])],
        )
    assert result["success"], ASSERT["installation_failed"].format(
        failures=failure_summary(result))
