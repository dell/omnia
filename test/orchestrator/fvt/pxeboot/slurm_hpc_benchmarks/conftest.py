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

"""Suite-local gate for destructive HPC benchmarks tests.

Tests carrying ``@pytest.mark.destructive`` (TC-08, TC-11, TC-18, TC-19) are
skipped unless the operator explicitly opts in via ``--run-destructive`` on the
pytest command line or by setting ``OMNIA_HPC_BENCHMARKS_DESTRUCTIVE=1`` in
the environment. This mirrors the opt-in pattern proposed for the PowerVault
destructive I/O suite so both suites share the same authorization surface.
"""

import os

import pytest


def pytest_addoption(parser):
    """Register the suite-local opt-in flag."""
    group = parser.getgroup("orchestrator-hpc-benchmarks")
    group.addoption(
        "--run-destructive",
        action="store_true",
        default=False,
        help=(
            "Run destructive HPC benchmarks tests (TC-08 pull_benchmarks, "
            "TC-11 air-gapped staging, TC-18 pre-existing dirs preservation, "
            "TC-19 staging idempotency). Off by default."
        ),
    )


def _destructive_authorized(config) -> bool:
    """Return True when destructive HPC benchmarks tests may run."""
    if config.getoption("--run-destructive", default=False):
        return True
    return os.environ.get("OMNIA_HPC_BENCHMARKS_DESTRUCTIVE", "").lower() in {
        "1",
        "true",
        "yes",
    }


def pytest_collection_modifyitems(config, items):
    """Skip destructive HPC benchmarks tests unless explicitly authorized."""
    if _destructive_authorized(config):
        return
    skip_destructive = pytest.mark.skip(
        reason=(
            "Destructive HPC benchmarks test: pass --run-destructive or set "
            "OMNIA_HPC_BENCHMARKS_DESTRUCTIVE=1 to authorize"
        )
    )
    suite_dir = os.path.dirname(os.path.abspath(__file__))
    for item in items:
        # Only gate items that live under this suite, so the flag stays scoped.
        try:
            item_path = os.path.abspath(str(item.fspath))
        except (AttributeError, TypeError):
            continue
        if not item_path.startswith(suite_dir):
            continue
        if item.get_closest_marker("destructive") is not None:
            item.add_marker(skip_destructive)
