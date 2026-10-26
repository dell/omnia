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
Installation — BuildStream Service Health Verification.

Validates the runtime build_stream.yml deployed:
  omnia_build_stream and omnia_postgres containers running
  playbook-watcher.service active
  every build_stream_db table present
  BuildStream API /health reports healthy
"""

import pytest

from library.functions import (
    TestLogger,
    failure_summary,
    verify_build_stream_services,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.installation
@pytest.mark.sanity
@pytest.mark.order(2101)
def test_build_stream_services(host):
    """Verify BuildStream containers, watcher, database tables and API health."""
    tc = TC["build_stream_services"]
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_build_stream_services(host)

    if result["success"]:
        tl.passed_fields(LOG["services_ok"], result["fields"])
    else:
        tl.failed_fields(LOG["services_failed"].format(count=len(result["failures"])),
                         result["fields"])
    assert result["success"], ASSERT["services_failed"].format(
        failures=failure_summary(result))
