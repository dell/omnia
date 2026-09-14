# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Live, explicitly selected verification for exact RPM repository cleanup.

Set ``REPO_MANAGER_TEST_CLEANUP_REPO`` to a disposable, fully-qualified Repo
Manager RPM repository identity before selecting this destructive scenario.
"""

import csv
import io
import os
import re
import shlex

import pytest

from library.functions import run_playbook
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


@pytest.mark.deploy
@pytest.mark.destructive
@pytest.mark.order(0)
def test_deploy_exact_repository_cleanup(host):
    """TC_RM_SCL_000: Clean only an explicitly named disposable RPM repository."""
    assert host is not None
    target, _version = _cleanup_target()
    result = run_playbook(
        tag="cleanup_repos",
        extra_vars={"cleanup_repos": target, "force": "true"},
    )
    assert result["success"], result.get("error", "Selective cleanup failed")


@pytest.mark.destructive
@pytest.mark.order(1)
def test_exact_repository_is_absent_while_pulp_is_healthy(host):
    """TC_RM_SCL_001: Distinguish verified absence from endpoint failure."""
    target, _version = _cleanup_target()
    health = host.run("/usr/local/bin/pulp status")
    assert health.rc == 0, health.stderr
    query = host.run(
        "/usr/local/bin/pulp rpm repository show --name " + shlex.quote(target)
    )
    assert query.rc != 0, f"Repository still exists after cleanup: {target}"
    query_output = f"{query.stdout}\n{query.stderr}".lower()
    assert any(marker in query_output for marker in NOT_FOUND_MARKERS), (
        "Repository state is unknown after cleanup; Pulp query failed without "
        f"an explicit not-found response: {query.stderr}"
    )


@pytest.mark.destructive
@pytest.mark.order(2)
def test_selective_cleanup_invalidates_repo_status(host):
    """TC_RM_SCL_002: Stale consumer URLs are removed after verified cleanup."""
    _cleanup_target()
    repo_status = f"{_get_output_path()}/repo_status.yml"
    assert not host.file(repo_status).exists, (
        f"Stale repo_status.yml remains after cleanup: {repo_status}"
    )


@pytest.mark.destructive
@pytest.mark.order(3)
def test_cleanup_status_records_exact_success(host):
    """TC_RM_SCL_003: Cleanup CSV records the requested identity successfully."""
    target, version = _cleanup_target()
    status_path = (
        f"{_get_base_path()}/log/rhel/{version}/cleanup/cleanup_status.csv"
    )
    status_file = host.file(status_path)
    assert status_file.exists, f"Cleanup status is missing: {status_path}"
    rows = list(csv.DictReader(io.StringIO(status_file.content_string)))
    matches = [row for row in rows if row.get("name") == target]
    assert len(matches) == 1, f"Expected one cleanup result for {target}: {rows}"
    assert matches[0].get("status") == "Success", matches[0]
