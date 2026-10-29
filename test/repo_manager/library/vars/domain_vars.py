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
    "repo_sync",
    "status",
    "cleanup",
    "cleanup_repos",
    "catalog_generate",
    "catalog_add",
    "catalog_delete",
    "catalog_validate",
    "user_registry",
]

# =====================================================================
# Pytest markers supported by this domain
# =====================================================================

MARKERS: List[str] = [
    "sanity",
    "functional",
    "positive",
    "destructive",
    "deploy",
    "x86_64",
    "aarch64",
    "nft",
    "performance",
    "idempotency",
    "security",
]

# =====================================================================
# Suite directories per FVT tag
# =====================================================================

SUITES: Dict[str, List[str]] = {
    "precheck": ["config"],
    "prepare": ["pulp"],
    "execute": ["repos", "artifacts", "policy"],
    "status": ["status"],
    "cleanup": ["cleanup"],
    "cleanup_repos": ["selective"],
    "catalog_generate": ["generate"],
    "catalog_add": ["add"],
    "catalog_delete": ["delete"],
    "catalog_validate": ["validate"],
    "user_registry": ["validation"],
}

# Ordered, non-destructive lifecycle used by an untagged ``exec`` or ``test``.
# Cleanup remains explicit-only and catalog mutation requires an exact suite.
ALL_EXEC_TAGS: List[str] = ["precheck", "prepare", "execute", "status", "user_registry"]
ALL_EXEC_MARKER: str = ""
ALL_VERIFY_EXCLUDE_MARKERS: List[str] = ["destructive"]

# These scenarios validate existing state and own no deployment trigger.
VERIFY_ONLY_TAGS: List[str] = ["user_registry"]

# Tags that require an explicit --suite argument (empty after catalog split).
REQUIRED_SUITE_TAGS: List[str] = []

# Suites that own a deployment lifecycle per tag (empty after catalog split).
SUITE_EXEC_OWNERS: Dict[str, List[str]] = {}

# Suites that only verify (no playbook deploy step of their own).
VERIFY_ONLY_SUITES: Dict[str, List[str]] = {
    "execute": ["policy"],
}

# =====================================================================
# Tags excluded from "all" verify (run only when explicit)
# =====================================================================

EXCLUDE_TAGS: List[str] = [
    "cleanup",
    "cleanup_repos",
    "catalog_generate",
    "catalog_add",
    "catalog_delete",
    "catalog_validate",
]
