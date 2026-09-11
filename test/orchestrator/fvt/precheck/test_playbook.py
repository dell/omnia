# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Precheck lifecycle execution and input verification."""

import pytest

from library.functions import (
    TestLogger,
    check_input_config_exists,
    check_network_spec_exists,
    run_playbook,
)


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_precheck(host):
    """ORCH_FVT_PRECHECK_E001: Execute the public precheck lifecycle tag."""
    tl = TestLogger("Deploy orchestrator precheck", "ORCH_FVT_PRECHECK_E001")
    result = run_playbook(tag="precheck")
    if result["success"]:
        tl.passed("Orchestrator precheck completed", result.get("output", ""))
    else:
        tl.failed("Orchestrator precheck failed", result.get("error", ""))
    assert result["success"], result.get("error", "Precheck failed")


@pytest.mark.sanity
@pytest.mark.order(1)
@pytest.mark.parametrize(
    ("check", "label"),
    [
        (check_input_config_exists, "orchestrator_config.yml"),
        (check_network_spec_exists, "network_spec.yml"),
    ],
)
def test_precheck_required_inputs(host, check, label):
    """ORCH_FVT_PRECHECK_V004: Required precheck inputs exist on the selected target."""
    result = check(host)
    assert result["success"], f"{label}: {result.get('error', result)}"
