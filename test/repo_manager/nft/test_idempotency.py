# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Repo Manager semantic idempotency verification."""

import yaml
import pytest

from library.functions import TestLogger, run_playbook
from library.vars.common_vars import OUTPUT_FILES, _get_output_path


def _read_repo_status(host):
    """Return the parsed generated status document."""
    status_path = f"{_get_output_path()}/{OUTPUT_FILES['repo_status']}"
    remote_file = host.file(status_path)
    assert remote_file.exists, f"Missing generated status: {status_path}"
    return yaml.safe_load(remote_file.content_string)


@pytest.mark.nft
@pytest.mark.idempotency
@pytest.mark.order(1)
def test_status_is_semantically_idempotent(host):
    """RM_NFT_001: Repeated status generation preserves its published contract."""
    first_run = run_playbook(tag="status", timeout=180)
    assert first_run["success"], first_run.get("error", "First status run failed")
    first_status = _read_repo_status(host)

    second_run = run_playbook(tag="status", timeout=180)
    assert second_run["success"], second_run.get(
        "error", "Second status run failed"
    )
    second_status = _read_repo_status(host)

    # Playbook execution has its own logger, so restore this test's identity
    # before emitting the final result captured by the report hook.
    test_log = TestLogger(
        "NFT: status semantic idempotency", "RM_NFT_001"
    )
    stable = first_status == second_status
    if stable:
        test_log.passed(
            "Repeated status generation is semantically stable",
            "Both runs completed successfully and produced identical YAML data.",
        )
    else:
        test_log.failed(
            "Repeated status generation changed published data",
            "repo_status.yml differed between two consecutive status runs.",
        )

    assert stable, "repo_status.yml changed between consecutive status runs"
