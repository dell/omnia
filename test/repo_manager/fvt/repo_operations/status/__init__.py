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
Repo Operations — Status suite.

ansible-playbook repo_manager.yml --tags status

Generates repo_status.yml and verifies its content.

Reference: src/repo_manager/playbooks/repo_operations/generate_repo_status.yml

TC_ST_000: Run repo_manager.yml --tags status
TC_ST_002: Verify Pulp container running (prerequisite)
TC_ST_003: Verify repo_status.yml exists
TC_ST_004: Verify repo_status.yml has expected content
"""
