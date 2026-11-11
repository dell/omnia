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

"""Suite-local gate for destructive CoreDNS/CoreDHCP tests.

Tests carrying ``@pytest.mark.destructive`` (TC-08 node-addition pipeline,
TC-09 SMD-unavailable cached-resolution) are skipped unless the operator
explicitly opts in via ``OMNIA_COREDNS_DESTRUCTIVE=1``. Uses only the
environment variable (no CLI option) to avoid duplicate-option conflicts
with other suite-local conftests that register their own opt-in flag.
"""

import os

import pytest


def _destructive_authorized() -> bool:
    """Return True when destructive CoreDNS/CoreDHCP tests may run."""
    return os.environ.get("OMNIA_COREDNS_DESTRUCTIVE", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    """Skip destructive CoreDNS/CoreDHCP tests unless explicitly authorized."""
    if _destructive_authorized():
        return
    skip_destructive = pytest.mark.skip(
        reason=(
            "Destructive CoreDNS/CoreDHCP test: set "
            "OMNIA_COREDNS_DESTRUCTIVE=1 to authorize (pauses SMD container "
            "briefly)"
        )
    )
    suite_dir = os.path.dirname(os.path.abspath(__file__))
    for item in items:
        try:
            item_path = os.path.abspath(str(item.fspath))
        except (AttributeError, TypeError):
            continue
        if not item_path.startswith(suite_dir):
            continue
        if item.get_closest_marker("destructive") is not None:
            item.add_marker(skip_destructive)
