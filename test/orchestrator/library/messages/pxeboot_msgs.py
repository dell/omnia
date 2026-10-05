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

"""Operator-facing messages for PXE and post-boot verification."""

TEST_LOG_MSGS = {
    "playbook_success": "Orchestrator PXE boot completed successfully",
    "playbook_failed": "Orchestrator PXE boot failed",
    "check_passed": "{component} verification passed",
    "check_failed": "{component} verification failed",
    "check_skipped": "{component} verification skipped",
}

TEST_ASSERT_MSGS = {
    "playbook_failed": (
        "orchestrator.yml --tags pxeboot failed with rc={rc} after "
        "{duration:.1f}s. Review pxeboot_status.yml, failed_nodes.json, and "
        "the failed node's cloud-init output before retrying."
    ),
    "verification_failed": (
        "{component} verification failed: {error}. Review the role-wise "
        "details above, correct the node or cluster state, and rerun PXE "
        "verification."
    ),
}
