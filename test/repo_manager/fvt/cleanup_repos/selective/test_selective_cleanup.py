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
Repo Manager Cleanup Repos — Selective Cleanup Verification.

Validates that the exact repository cleanup succeeded:
  Target repository is absent while Pulp is healthy
  Stale consumer URLs removed after cleanup
  Cleanup CSV records the requested identity
"""

import csv
import io
import os
import re
import shlex

import pytest

from library.functions import TestLogger
from library.vars import TEST_CASES as TC
from library.vars.common_vars import _get_base_path, _get_output_path


TARGET_ENVIRONMENT_VARIABLE = "REPO_MANAGER_TEST_CLEANUP_REPO"
TARGET_PATTERN = re.compile(
    r"^(x86_64|aarch64)_rhel_(\d+\.\d+)_([A-Za-z0-9_.-]+)$"
)
NOT_FOUND_MARKERS = (
    "not found",
    "does not exist",
    "could not find",
    "matches the given query",
    "404",
)


def _cleanup_target():
    """Return the explicitly authorized disposable cleanup target."""
    target = os.environ.get(TARGET_ENVIRONMENT_VARIABLE, "").strip()
    assert target, (
        f"{TARGET_ENVIRONMENT_VARIABLE} must name a disposable exact RPM "
        "repository before running cleanup_repos FVT"
    )
    match = TARGET_PATTERN.fullmatch(target)
    assert match and target.lower() != "all", (
        "Selective cleanup FVT requires an exact "
        "<arch>_rhel_<version>_<repo> identity"
    )
    return target, match.group(2)


@pytest.mark.destructive
@pytest.mark.order(1)
def test_exact_repository_is_absent(host):
    """Verify target repository is absent while Pulp is healthy."""
    tc = TC["exact_repository_absent"]
    tl = TestLogger(tc["title"], tc["id"])
    target, _version = _cleanup_target()
    health = host.run("/usr/local/bin/pulp status")
    assert health.rc == 0, health.stderr
    query = host.run(
        "/usr/local/bin/pulp rpm repository show --name " + shlex.quote(target)
    )

    if query.rc != 0:
        query_output = f"{query.stdout}\n{query.stderr}".lower()
        if any(marker in query_output for marker in NOT_FOUND_MARKERS):
            tl.passed(
                f"Repository {target} confirmed absent",
                query_output.strip(),
            )
        else:
            tl.failed(
                f"Repository state unknown for {target}",
                query_output.strip(),
            )
            assert False, (
                "Repository state is unknown after cleanup; Pulp query failed "
                f"without an explicit not-found response: {query.stderr}"
            )
    else:
        tl.failed(f"Repository still exists after cleanup: {target}", "")
        assert False, f"Repository still exists after cleanup: {target}"


@pytest.mark.destructive
@pytest.mark.order(2)
def test_selective_cleanup_invalidates_repo_status(host):
    """Verify stale consumer URLs removed after cleanup."""
    tc = TC["cleanup_invalidates_repo_status"]
    tl = TestLogger(tc["title"], tc["id"])
    _cleanup_target()
    repo_status = f"{_get_output_path()}/repo_status.yml"
    exists = host.file(repo_status).exists

    if not exists:
        tl.passed("Stale repo_status.yml removed after cleanup", repo_status)
    else:
        tl.failed(f"Stale repo_status.yml remains: {repo_status}", "")

    assert not exists, (
        f"Stale repo_status.yml remains after cleanup: {repo_status}"
    )


@pytest.mark.destructive
@pytest.mark.order(3)
def test_cleanup_status_records_success(host):
    """Verify cleanup CSV records the requested identity."""
    tc = TC["cleanup_status_records_success"]
    tl = TestLogger(tc["title"], tc["id"])
    target, version = _cleanup_target()
    status_path = (
        f"{_get_base_path()}/log/rhel/{version}/cleanup/cleanup_status.csv"
    )
    status_file = host.file(status_path)
    assert status_file.exists, f"Cleanup status is missing: {status_path}"
    rows = list(csv.DictReader(io.StringIO(status_file.content_string)))
    matches = [row for row in rows if row.get("name") == target]

    if len(matches) == 1 and matches[0].get("status") == "Success":
        tl.passed(
            f"Cleanup CSV records success for {target}",
            f"Path: {status_path}",
        )
    else:
        tl.failed(
            f"Expected one successful cleanup result for {target}",
            f"Matches: {matches}",
        )

    assert len(matches) == 1, f"Expected one cleanup result for {target}: {rows}"
    assert matches[0].get("status") == "Success", matches[0]
