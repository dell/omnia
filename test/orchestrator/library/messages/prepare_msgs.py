# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Operator-facing messages for Orchestrator prepare verification."""

TEST_LOG_MSGS = {
    "playbook_success": "Orchestrator prepare completed successfully",
    "playbook_failed": "Orchestrator prepare failed",
    "check_passed": "{component} verification passed",
    "check_failed": "{component} verification failed",
    "check_skipped": "{component} verification skipped",
}


TEST_ASSERT_MSGS = {
    "playbook_failed": (
        "orchestrator.yml --tags prepare failed with rc={rc} after "
        "{duration:.1f}s. Review the playbook output and the active "
        "project's Orchestrator log before retrying."
    ),
    "verification_failed": (
        "{component} verification failed: {error}. Review the structured "
        "result fields and the corresponding systemd/container logs."
    ),
}
