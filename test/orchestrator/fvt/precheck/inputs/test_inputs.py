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

"""Required and conditionally selected project-input contracts."""

import pytest
from library.functions import (
    TestLogger,
    check_precheck_inputs,
)
from library.vars import TEST_CASES as TC

from fvt.result import verify_precheck


@pytest.mark.sanity
@pytest.mark.order(10501)
def test_precheck_inputs(host):
    """Require every source-selected Orchestrator input to be non-empty."""
    tc = TC["precheck_inputs"]
    test_log = TestLogger(tc["title"], tc["id"])
    verify_precheck(test_log, tc, host, check_precheck_inputs)
