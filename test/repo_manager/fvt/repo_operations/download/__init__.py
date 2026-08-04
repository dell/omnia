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
Repo Operations — Download suite.

ansible-playbook repo_manager.yml --tags download

Downloads and syncs packages/repositories into Pulp,
generates repo_status.yml.

Reference: src/repo_manager/playbooks/repo_operations/download.yml

Suites:
    repos/      — TC_DL_002-004: Repository sync and status file verification
    packages/   — TC_DL_005: Package download status verification
"""
