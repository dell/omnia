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
Repo Manager Catalog Add — Deploy (catalog_add tag).

Deploy repo_manager.yml --tags catalog_add
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.vars import TEST_CASES as TC
from library.vars.common_vars import _get_input_path
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_catalog_add(host):
    """Deploy repo_manager --tags catalog_add."""
    input_path = _get_input_path()
    input_file = f"{input_path}/additions.txt"
    result = host.run(f"test -f {input_file} && echo 'exists' || echo 'missing'")

    if "missing" in result.stdout:
        tl = TestLogger("Deploy repo_manager (catalog_add)", "RM_FVT_CATALOG_ADD_E001")
        tl.skipped_fields(
            "Catalog add input file not found",
            {
                "File": input_file,
                "Status": "missing",
                "Tag": "catalog_add",
            }
        )
        pytest.skip(f"Input file not found: {input_file}")

    tc = TC["deploy_catalog_add"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(
        tag="catalog_add",
        extra_vars={"input_file": input_file},
    )

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(
            duration=result["duration"]
        ))
    else:
        tl.failed(
            LOG["playbook_failed"].format(
                rc=result["rc"], duration=result["duration"],
            ),
            result.get("error", "See playbook output above"),
        )

    assert result["success"], ASSERT["playbook_failed"].format(
        playbook="repo_manager.yml", tag="catalog_add",
        rc=result["rc"], duration=result["duration"],
    )
