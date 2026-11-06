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


"""Messages of the cleanup preview (./setup_env.sh --cleanup --dry-run)."""

CLEANUP_DRY_MSGS = {
    "domains": "    domain-init.sh --cleanup runs for: {domains}",
    "report_inside": "    WARNING: the report folder of the current run is inside the data "
                     "path; a real cleanup would refuse: {path}",
    "done": "DRY RUN: nothing was changed or deleted. ./setup_env.sh --cleanup does it (it "
            "asks for 'yes'; --yes confirms without asking)",
}
