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

"""Operator-facing messages for full Orchestrator cleanup verification."""

TEST_LOG_MSGS = {
    "playbook_success": "Full Orchestrator cleanup completed successfully",
    "playbook_failed": "Full Orchestrator cleanup failed",
    "check_passed": "{component} verification passed",
    "check_failed": "{component} verification failed",
}

TEST_ASSERT_MSGS = {
    "playbook_failed": (
        "orchestrator.yml --tags cleanup failed with rc={rc} after "
        "{duration:.1f}s. Review the cleanup summary and component error "
        "reported in the playbook output."
    ),
    "verification_failed": (
        "{component} verification failed: {error}. Review the structured "
        "cleanup postconditions above."
    ),
}
