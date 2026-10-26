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

"""BuildStream system test — validation-runner configuration."""

# =====================================================================
# Domain identity (runner category: e2e_build_stream)
# =====================================================================

DOMAIN_NAME: str = "build_stream"
CATEGORY: str = "e2e_build_stream"
TAG_ROOT: str = "e2e"

# =====================================================================
# E2E tags — each maps to a subdirectory under e2e/, in run order
# =====================================================================

E2E_TAGS: list[str] = [
    "prepare_base",
    "installation",
    "auto_cleanup",
    "cleanup",
]

# =====================================================================
# Pytest markers supported by this suite (runner allowlist)
# =====================================================================

MARKERS: list[str] = [
    "sanity",
    "deploy",
    "precheck",
    "destructive",
    "e2e",
    "br_86010",
    "prepare_base",
    "installation",
    "pipeline",
    "cadence",
    "cleanup",
    "auto_cleanup",
]

# =====================================================================
# Suite directories per tag
# =====================================================================

SUITES: dict[str, list[str]] = {
    "prepare_base": ["readiness"],
    "installation": ["health", "repository", "build", "deploy", "cadence"],
    "auto_cleanup": ["verification"],
    "cleanup": ["postconditions"],
}

# An untagged run covers base preparation and installation. auto_cleanup
# deletes image groups and cleanup removes every domain, so both run only
# when selected explicitly.
ALL_EXEC_TAGS: list[str] = ["prepare_base", "installation"]
ALL_EXEC_MARKER: str = "sanity"
ALL_VERIFY_EXCLUDE_MARKERS: list[str] = ["destructive"]

VERIFY_ONLY_TAGS: list[str] = []
REQUIRED_SUITE_TAGS: list[str] = []
VERIFY_ONLY_SUITES: dict[str, list[str]] = {}
SUITE_EXEC_OWNERS: dict[str, list[str]] = {}

# =====================================================================
# Tags excluded from "all" verify (run only when explicit)
# =====================================================================

EXCLUDE_TAGS: list[str] = ["auto_cleanup", "cleanup"]
