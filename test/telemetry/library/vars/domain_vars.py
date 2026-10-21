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
Telemetry — Domain-specific validation variables.

Defines FVT tags, pytest markers, suite directories, and cleanup
exclusions used by ``ValidationRunner`` for this domain.

To register a new domain, create a similar file in that domain's
``library/vars/`` folder and import it in ``_run.py``.
"""

from typing import Dict, List

# =====================================================================
# Domain identity
# =====================================================================

DOMAIN_NAME: str = "telemetry"

# =====================================================================
# FVT tags — each maps to a subdirectory under fvt/
# =====================================================================

FVT_TAGS: List[str] = [
    "precheck",
    "validate",
    "deploy",
    "deploy_sinks",
    "cleanup",
    "cleanup_sinks",
    "cleanup_idrac",
    "cleanup_ldms",
    "cleanup_ome",
    "cleanup_powerscale",
    "cleanup_ufm",
    "cleanup_vast",
]

# =====================================================================
# Pytest markers supported by this domain
# =====================================================================

MARKERS: List[str] = [
    "sanity",
    "functional",
    "precheck",
    "sink",
    "source",
    "deploy",
    "ome",
    "ldms",
    "vast",
    "sfm",
    "ufm",
    "nft",
    "performance",
    "idempotency",
]

# =====================================================================
# Suite directories per FVT tag
# =====================================================================

SUITES: Dict[str, List[str]] = {
    "precheck": ["cluster"],
    "validate": ["input"],
    "deploy": ["sinks", "sources"],
    "deploy_sinks": [],
    "cleanup": ["cleanup", "status"],
    "cleanup_sinks": ["status"],
    "cleanup_idrac": [],
    "cleanup_ldms": [],
    "cleanup_ome": [],
    "cleanup_powerscale": [],
    "cleanup_ufm": [],
    "cleanup_vast": [],
}

# =====================================================================
# Advanced runner configuration (aligned with orchestrator pattern)
# =====================================================================

# Tags that require playbook execution during "all" runs.
ALL_EXEC_TAGS: List[str] = ["precheck", "validate", "deploy"]

# Default marker for exec phase.
ALL_EXEC_MARKER: str = "sanity"

# Markers excluded from broad verification runs.
ALL_VERIFY_EXCLUDE_MARKERS: List[str] = []

# Tags restricted to verify-only mode.
VERIFY_ONLY_TAGS: List[str] = []

# Tags requiring specific suite selection.
REQUIRED_SUITE_TAGS: List[str] = []

# Suites restricted to verify-only mode.
VERIFY_ONLY_SUITES: Dict[str, List[str]] = {}

# Suites that manage their own playbook execution.
SUITE_EXEC_OWNERS: Dict[str, List[str]] = {}

# =====================================================================
# Tags excluded from "all" verify (run only when explicit)
# =====================================================================

EXCLUDE_TAGS: List[str] = [
    "cleanup",
    "cleanup_sinks",
    "cleanup_idrac",
    "cleanup_ldms",
    "cleanup_ome",
    "cleanup_powerscale",
    "cleanup_ufm",
    "cleanup_vast",
]
