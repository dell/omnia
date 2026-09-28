# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Repo Manager response-time verification."""

from time import monotonic

import pytest

from omnia_auto import run_on_host
from library.functions import TestLogger
from library.vars.common_vars import CMDS


PULP_STATUS_THRESHOLD = 10.0


@pytest.mark.nft
@pytest.mark.performance
@pytest.mark.order(1)
def test_pulp_status_response_time(host):
    """RM_NFT_002: The local Pulp health command completes promptly."""
    test_log = TestLogger(
        "NFT: Pulp status response time", "RM_NFT_002"
    )
    started = monotonic()
    result = run_on_host(host, CMDS["pulp_status"])
    duration = monotonic() - started
    within_threshold = duration <= PULP_STATUS_THRESHOLD

    if result.rc == 0 and within_threshold:
        test_log.passed(
            "Pulp status completed within threshold",
            f"Duration: {duration:.2f}s; threshold: {PULP_STATUS_THRESHOLD:.1f}s",
        )
    else:
        test_log.failed(
            "Pulp status performance check failed",
            f"Return code: {result.rc}; duration: {duration:.2f}s; "
            f"threshold: {PULP_STATUS_THRESHOLD:.1f}s",
        )

    assert result.rc == 0, "pulp status failed"
    assert within_threshold, (
        f"pulp status took {duration:.2f}s; expected no more than "
        f"{PULP_STATUS_THRESHOLD:.1f}s"
    )
