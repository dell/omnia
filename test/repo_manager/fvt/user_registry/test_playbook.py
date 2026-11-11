# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
User Registry — Test Playbook Driver.

This file drives the user_registry tag's test suites:
- validation/   registry structure, TLS, auth, and reachability checks
- negative/     error handling and failure scenario tests

Usage:
    pytest fvt/user_registry/test_playbook.py
"""

import pytest

from library.functions import TestLogger, run_playbook
from library.vars import TEST_CASES as TC


@pytest.mark.deploy
@pytest.mark.order(1)
def test_deploy_user_registry(host):
    """Deploy repo_manager --tags user_registry."""
    tc = TC["deploy_user_registry"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(
        tag="user_registry",
        host=host,
    )

    if result["success"]:
        tl.passed("User registry playbook executed successfully", result["details"])
    else:
        tl.failed("User registry playbook execution failed", result["error"])

    assert result["success"], "User registry playbook must execute successfully"
