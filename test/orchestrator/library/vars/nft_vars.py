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

"""Immutable contracts for Orchestrator non-functional tests."""

NFT_LIFECYCLE_TAGS: tuple[str, ...] = (
    "precheck",
    "prepare",
    "provision",
    "cleanup",
)

NFT_THRESHOLD_CONFIG_KEY = "nft_performance_threshold_seconds"
NFT_TIMEOUT_GRACE_SECONDS = 300

NON_PERSISTENT_CHANGE_TASK_PREFIXES: tuple[str, ...] = (
    "orchestrator_setup : Create OIM host group",
)

ORCHESTRATOR_CREDENTIAL_FILE = "orchestrator_credentials.yml"
ORCHESTRATOR_VAULT_KEY_FILE = ".orchestrator_credentials_key"
ORCHESTRATOR_SSH_PRIVATE_KEY = "/root/.ssh/oim_rsa"
ORCHESTRATOR_LOG_DIRECTORY = "/var/log/omnia/orchestrator"

ALLOWED_CREDENTIAL_MODES: frozenset[str] = frozenset({"600", "640"})
REQUIRED_PRIVATE_KEY_MODE = "600"
VAULT_HEADER_PATTERN = r"^\$ANSIBLE_VAULT;1\.[12];AES256$"
