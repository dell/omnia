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
Build Stream -- Domain-specific validation variables.

Defines FVT tags, pytest markers, suite directories, and cleanup
exclusions used by ``ValidationRunner`` for this domain.

To register a new domain, create a similar file in that domain's
``library/vars/`` folder and import it in ``_run.py``.
"""

from typing import Dict, List

# =====================================================================
# Domain identity
# =====================================================================

DOMAIN_NAME: str = "build_stream"
ENABLE_UT: bool = False

# =====================================================================
# FVT tags -- each maps to a subdirectory under fvt/
# =====================================================================

FVT_TAGS: List[str] = [
    "prepare_base",
    "precheck",
    "prepare",
    "execute",
    "cleanup",
]

# A no-tag FVT command follows this lifecycle.  ``test`` performs
# exec + verify for each scenario before advancing to the next one.
# No default marker: without --marker every collected test runs.
ALL_EXEC_TAGS: List[str] = [
    "precheck",
    "prepare",
    "execute",
]
ALL_EXEC_MARKER: str = ""

# =====================================================================
# Pytest markers supported by this domain
# =====================================================================

MARKERS: List[str] = [
    "sanity",
    "deploy",
    "pipeline",
    "build_pipeline",
    "deploy_pipeline",
    "cadence",
    "cleanup_pipeline",
    "automatic_cleanup",
    "automatic_execution",
    "manual_execution",
    "nft",
    "resilience",
    "security",
    "disruptive",
]

# =====================================================================
# Suite directories per FVT tag
# =====================================================================

SUITES: Dict[str, List[str]] = {
    "prepare_base": ["readiness"],
    "precheck": ["environment", "containers", "credentials"],
    "prepare": ["build_stream"],
    "execute": [
        "gitlab_server",
        "gitlab_runner",
        "gitlab_project",
        "build_automatic",
        "build_manual",
        "deploy_automatic",
        "deploy_manual",
        "cadence",
        "auto_cleanup",
        "pipeline_cleanup",
    ],
    "cleanup": ["gitlab", "build_stream"],
}

# =====================================================================
# Tags excluded from "all" verify (run only when explicit)
# =====================================================================

EXCLUDE_TAGS: List[str] = [
    "prepare_base",
    "cleanup",
]
