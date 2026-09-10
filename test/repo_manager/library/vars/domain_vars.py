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
}

# Ordered deploy stages used by an untagged ``test`` or ``exec`` command.
ALL_EXEC_TAGS: List[str] = [
    "precheck",
    "prepare",
    "execute",
    "status",
]
ALL_EXEC_MARKER: str = "sanity"
ALL_VERIFY_EXCLUDE_MARKERS: List[str] = ["negative", "destructive"]

# Catalog is an umbrella for distinct public operations. Lifecycle execution
# must select exactly one operation; negative catalog checks are verify-only.
REQUIRED_SUITE_TAGS: List[str] = ["catalog"]
VERIFY_ONLY_TAGS: List[str] = ["policy", "negative"]
VERIFY_ONLY_SUITES: Dict[str, List[str]] = {
    "catalog": ["negative"],
}

# =====================================================================
# Tags excluded from "all" verify (run only when explicit)
# =====================================================================

EXCLUDE_TAGS: List[str] = [
    "cleanup",
    "cleanup_repos",
    "negative",
    "catalog",
]
