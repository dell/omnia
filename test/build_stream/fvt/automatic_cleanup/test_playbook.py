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

"""Execute one production automatic-cleanup cycle against an explicit target."""

import pytest

from library.functions import TestLogger, run_automatic_cleanup_cycle
from library.vars import TEST_CASES as TC


@pytest.mark.sanity
@pytest.mark.deploy
@pytest.mark.disruptive
@pytest.mark.order(1)
def test_execute_automatic_cleanup(host, automatic_cleanup_state):
    """Run cleanup_cron only when the configured Job is the sole FAILED target."""
    case = TC["execute_automatic_cleanup"]
    logger = TestLogger(case["title"], case["id"])
    result = run_automatic_cleanup_cycle(host, automatic_cleanup_state.job_id)
    assert result["success"], result["error"]
    assert result["image_group_id"] == automatic_cleanup_state.image_group_id
    logger.passed(
        "Production automatic-cleanup cron accepted the explicit FAILED "
        f"ImageGroup {result['image_group_id']}"
    )
