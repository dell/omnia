# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager Catalog Validate — Deploy (catalog_validate tag).

Deploy repo_manager.yml --tags catalog_validate
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_catalog_validate(host):
    """Deploy repo_manager --tags catalog_validate."""
    tc = TC["deploy_catalog_validate"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(
        tag="catalog_validate",
        host=host,
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
        playbook="repo_manager.yml", tag="catalog_validate",
        rc=result["rc"], duration=result["duration"],
    )
