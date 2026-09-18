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

"""Omnia Main domain settings for the shared validation runner."""

from typing import Dict, List

DOMAIN_NAME: str = "main"

FVT_TAGS: List[str] = [
    "setup",
    "init",
    "precheck",
    "validate",
    "cli",
    "omnia_cli",
    "cleanup",
]

MARKERS: List[str] = [
    "sanity",
    "functional",
    "regression",
    "deploy",
    "cleanup",
]

SUITES: Dict[str, List[str]] = {
    "setup": [
        "environment", "directories", "virtual_environment", "lifecycle",
    ],
    "init": ["domain_init", "lifecycle"],
    "cli": ["commands", "prepare_base", "tags"],
    "omnia_cli": ["diagnostics", "errors", "logs"],
    "precheck": [],
    "validate": [],
    "cleanup": [],
}

# Cleanup changes installation state and must be requested explicitly.
EXCLUDE_TAGS: List[str] = ["cleanup"]

# A complete Main run executes each positive lifecycle entry once, in order.
# Extended, negative, and rerun cases remain available through their markers.
ALL_EXEC_TAGS: List[str] = [
    "setup",
    "init",
    "precheck",
    "validate",
    "cli",
    "omnia_cli",
]
ALL_EXEC_MARKER: str = "sanity"
