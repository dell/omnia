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
Orchestrator Precheck — Deploy.

TC_PC_000: Deploy orchestrator.yml --tags precheck
"""

import pytest

from library.functions import TestLogger, run_playbook


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_precheck(_host):
    """TC_PC_000: Deploy orchestrator.yml --tags precheck."""
    tl = TestLogger(
        "Deploy Playbook (precheck)",
        "TC_PC_000"
    )
    result = run_playbook(tag="precheck")

    if result["success"]:
        tl.passed(f"Playbook execution succeeded in {result['duration']}s")
    else:
        tl.failed(
            f"Playbook execution failed with RC {result['rc']}",
            result.get("error", "See playbook output above"),
        )

    assert result["success"], f"Playbook execution failed: RC {result['rc']}"
