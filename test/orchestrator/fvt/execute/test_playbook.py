# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Execute lifecycle deployment trigger."""

import pytest

from library.functions import TestLogger, run_playbook


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(0)
def test_deploy_execute(host):
    """ORCH_FVT_EXECUTE_E001: Execute provisioning through the public execute tag."""
    tl = TestLogger("Deploy orchestrator execute lifecycle", "ORCH_FVT_EXECUTE_E001")
    result = run_playbook(tag="execute", timeout=7200)
    if result["success"]:
        tl.passed("Orchestrator execute lifecycle completed")
    else:
        tl.failed("Orchestrator execute lifecycle failed", result.get("error", ""))
    assert result["success"], result.get("error", "Execute lifecycle failed")
