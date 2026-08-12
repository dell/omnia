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
Repo Operations scenario — download and status operations.

Mirrors src/repo_manager/playbooks/repo_operations/ which contains:
    - download.yml (--tags download)
    - generate_repo_status.yml (--tags status)

Suites:
    download/   — TC_DL_000-005: Download packages/repos and verify sync
    status/     — TC_ST_000-004: Generate and verify repo_status.yml
"""
