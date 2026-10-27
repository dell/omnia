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

"""BuildStream system verification test (SVT) — validation-runner configuration."""

# =====================================================================
# Domain identity (runner category: svt_build_stream)
# =====================================================================

DOMAIN_NAME: str = "build_stream"
CATEGORY: str = "svt_build_stream"
TAG_ROOT: str = "svt"

# =====================================================================
# SVT scenarios — each maps to a subdirectory under svt/, in run order
# =====================================================================

SVT_TAGS: list[str] = [
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
    "svt",
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

# The full flow (no scenario given) runs every scenario in order and every
# test (no marker filter). It ends with cleanup, which removes the domains
# enabled under "cleanup" in test_config.yml.
ALL_EXEC_TAGS: list[str] = list(SVT_TAGS)
ALL_EXEC_MARKER: str = ""
ALL_VERIFY_EXCLUDE_MARKERS: list[str] = []

VERIFY_ONLY_TAGS: list[str] = []
REQUIRED_SUITE_TAGS: list[str] = []
VERIFY_ONLY_SUITES: dict[str, list[str]] = {}
SUITE_EXEC_OWNERS: dict[str, list[str]] = {}

# =====================================================================
# Scenarios excluded from an untagged verify (none: the full flow runs all)
# =====================================================================

EXCLUDE_TAGS: list[str] = []
