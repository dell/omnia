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
Orchestrator System Test (ST) — Suite-Local Configuration.

Test Plan: BR-55868 — RHEL 10.2 Support for x86_64 Functional Groups
ER: ER-ORCH-010-rhel-10-2-x86-64-support

Reporting: Inherits from domain-level conftest.py (orchestrator/conftest.py)
"""

import pytest

# ============================================================================
# Fixtures: Test Logging
# ============================================================================

@pytest.fixture
def test_logger():
    """Provide the TestLogger class from omnia_auto."""
    from omnia_auto import TestLogger as OmniaTestLogger
    return OmniaTestLogger


# ============================================================================
# Hooks: Test Collection
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Add ST-specific markers to all tests in this directory."""
    for item in items:
        # Add 'st' marker to all tests in this directory
        if "st" not in [marker.name for marker in item.iter_markers()]:
            item.add_marker(pytest.mark.st)
        # Add 'orchestrator' marker
        if "orchestrator" not in [marker.name for marker in item.iter_markers()]:
            item.add_marker(pytest.mark.orchestrator)


def pytest_configure(config):
    """Register ST-specific markers."""
    config.addinivalue_line("markers", "st: system test (spans multiple domains)")
    config.addinivalue_line("markers", "tier2: Tier 2 - Provisioning & Integration tests")
    config.addinivalue_line("markers", "tier3: Tier 3 - Guards & Error Handling tests")
    config.addinivalue_line("markers", "tier4: Tier 4 - Day-2 Operations tests")
    config.addinivalue_line("markers", "orchestrator: orchestrator domain tests")
    config.addinivalue_line("markers", "rhel102: RHEL 10.2 EUS specific tests")
    config.addinivalue_line("markers", "node_lifecycle: Node add/delete checks; run only when --marker selects node_lifecycle")
