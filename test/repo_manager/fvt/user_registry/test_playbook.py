# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
User Registry — Test Playbook Driver.

Runs the precheck tag which includes user_registry validation
via the validation role.

- validation/   registry structure, TLS, auth, and reachability checks

Usage:
    pytest fvt/user_registry/test_playbook.py
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.deploy
@pytest.mark.order(1)
def test_deploy_user_registry(host):
    """Deploy repo_manager --tags precheck (includes user_registry validation)."""
    tc = TC["deploy_user_registry"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(tag="precheck")

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
        playbook="repo_manager.yml", tag="precheck",
        rc=result["rc"], duration=result["duration"],
    )
