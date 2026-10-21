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

"""OpenLDAP postconditions produced by full Orchestrator cleanup."""

import pytest
from library.functions import (
    TestLogger,
    check_cleanup_openldap,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_cleanup


@pytest.mark.sanity
@pytest.mark.destructive
@pytest.mark.order(50201)
def test_openldap_removed(host):
    """Verify the OpenLDAP proxy service, container and state are removed."""
    tc = TC["cleanup_openldap"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_cleanup(test_log, host, "OpenLDAP cleanup", check_cleanup_openldap)
