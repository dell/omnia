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
Repo Manager — Domain-specific validation variables.

Defines FVT tags, pytest markers, suite directories, and cleanup
exclusions used by ``ValidationRunner`` for this domain.

To register a new domain, create a similar file in that domain's
``library/vars/`` folder and import it in ``_run.py``.
"""

from typing import Dict, List

# =====================================================================
# Domain identity
# =====================================================================

DOMAIN_NAME: str = "repo_manager"

# =====================================================================
# FVT tags — each maps to a subdirectory under fvt/
# =====================================================================

FVT_TAGS: List[str] = [
    "precheck",
    "prepare",
    "execute",
    "status",
    "cleanup",
    "cleanup_repos",
    "policy",
    "negative",
    "catalog",
    "user_registry",
    "repo_sync",
]

# =====================================================================
# Pytest markers supported by this domain
# =====================================================================

MARKERS: List[str] = [
    "sanity",
    "functional",
    "positive",
    "negative",
    "destructive",
    "deploy",
    "x86_64",
    "aarch64",
    "nft",
    "performance",
    "idempotency",
    "security",
    "repo_resync",
]

# =====================================================================
# Suite directories per FVT tag
# =====================================================================

SUITES: Dict[str, List[str]] = {
    "precheck": [],
    "prepare": [],
    "execute": [],
    "status": [],
    "cleanup": [],
    "cleanup_repos": [],
    "policy": [],
    "negative": ["error_scenarios"],
    "catalog": ["add", "delete", "generate", "negative", "validate"],
    "user_registry": [],
    "repo_sync": [],
}

# Ordered, non-destructive lifecycle used by an untagged ``exec`` or ``test``.
# Cleanup remains explicit-only and catalog mutation requires an exact suite.
ALL_EXEC_TAGS: List[str] = ["precheck", "prepare", "execute", "status"]
ALL_EXEC_MARKER: str = ""
ALL_VERIFY_EXCLUDE_MARKERS: List[str] = ["negative", "destructive"]

# These scenarios validate existing state and own no deployment trigger.
VERIFY_ONLY_TAGS: List[str] = ["policy", "negative", "user_registry"]

# Catalog operations are ambiguous without one exact operation suite. The
# negative suite verifies validation behavior and never executes a playbook.
REQUIRED_SUITE_TAGS: List[str] = ["catalog"]
VERIFY_ONLY_SUITES: Dict[str, List[str]] = {"catalog": ["negative"]}
SUITE_EXEC_OWNERS: Dict[str, List[str]] = {
    "catalog": ["add", "delete", "generate", "validate"],
}

# =====================================================================
# Tags excluded from "all" verify (run only when explicit)
# =====================================================================

EXCLUDE_TAGS: List[str] = [
    "cleanup",
    "cleanup_repos",
    "repo_sync",
]
