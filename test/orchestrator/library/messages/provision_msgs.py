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

"""Operator-facing messages for Orchestrator provision verification."""

TEST_LOG_MSGS = {
    "playbook_success": "Orchestrator provision completed successfully",
    "playbook_failed": "Orchestrator provision failed",
    "check_passed": "{component} verification passed",
    "check_failed": "{component} verification failed",
}

TEST_ASSERT_MSGS = {
    "playbook_failed": (
        "orchestrator.yml --tags provision failed with rc={rc} after "
        "{duration:.1f}s.\n"
        "HOW TO FIX:\n"
        "  1. Review the failed Ansible task and the active project's log.\n"
        "  2. Correct the reported input, dependency, or service failure.\n"
        "  3. Rerun the provision tag before running verification."
    ),
    "verification_failed": (
        "{component} verification failed: {error}.\n"
        "HOW TO FIX:\n"
        "  1. Review the functional-group and node details above.\n"
        "  2. Compare the PXE mapping with SMD, Boot Service, and Metadata "
        "Service state.\n"
        "  3. Correct the conflicting state and rerun provision verification."
    ),
}
