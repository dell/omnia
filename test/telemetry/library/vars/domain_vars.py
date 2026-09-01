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
    "cleanup",
]

# =====================================================================
# Pytest markers supported by this domain
# =====================================================================

MARKERS: List[str] = [
    "sanity",
    "functional",
    "sink",
    "source",
    "deploy",
    "ome",
    "ldms",
    "sfm",
    "ufm",
]

# =====================================================================
# Suite directories per FVT tag
# =====================================================================

SUITES: Dict[str, List[str]] = {
    "precheck": ["cluster"],
    "validate": ["input"],
    "deploy": ["sinks", "sources"],
    "cleanup": ["cleanup"],
}

# =====================================================================
# Tags excluded from "all" verify (run only when explicit)
# =====================================================================

EXCLUDE_TAGS: List[str] = [
    "cleanup",
]
