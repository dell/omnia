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
NFT test for PowerScale metrics channel transitions.

This test validates playbook-level deployment and cleanup across
metrics_enabled flag variations.

Test Coverage:
- Metrics enable/disable transitions
- Idempotency verification
- Cleanup validation

Note: This test focuses on playbook-level validation (can we deploy with
different metrics_enabled values) rather than component-level verification
(which is covered by FVT tests).
Note: Logs are managed via PowerScale API, not by Omnia, so only metrics
transitions are tested here.
"""

import pytest

from library.functions.playbook_runner import run_playbook
from library.functions.telemetry_func import load_telemetry_config_from_target

PLAYBOOK_ENTRY_POINT = "playbooks/telemetry.yml"
PLAYBOOK_WORKDIR = "src/telemetry"


def _cleanup_powerscale(host):
    """Clean up PowerScale components before deployment.

    Args:
        host: Testinfra host connection to the OIM.
    """
    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="cleanup_powerscale",
    )
    if result["rc"] != 0:
        pytest.fail(f"Cleanup failed with exit code {result['rc']}")


def _deploy_with_channels(host, tl, metrics_enabled, step_name, cleanup_first=True):
    """Deploy PowerScale with specific metrics configuration.

    Args:
        host: Testinfra host connection to the OIM.
        tl: TestLogger instance.
        metrics_enabled: Boolean for metrics channel.
        step_name: Name of the test step.
        cleanup_first: Whether to cleanup before deployment.
    """
    if cleanup_first:
        tl.check(f"[{step_name}] Cleaning up PowerScale components")
        _cleanup_powerscale(host)

    tl.check(f"[{step_name}] Deploying with metrics={metrics_enabled}")

    extra_vars = {
        "telemetry_config.telemetry_sources.powerscale.metrics_enabled": metrics_enabled,
        "telemetry_config.telemetry_sources.powerscale.logs_enabled": False,
    }

    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="execute",
        extra_vars=extra_vars,
    )

    if result["rc"] != 0:
        pytest.fail(f"[{step_name}] Deploy failed with exit code {result['rc']}")

    tl.info(f"[{step_name}] Deployment successful")


@pytest.mark.nft
@pytest.mark.source
def test_powerscale_channels_comprehensive(host):
    """Comprehensive test for PowerScale metrics channel transitions.

    Tests metrics enable/disable transitions:
    1. true (baseline - metrics enabled, logs disabled)
    2. false (metrics disabled, logs disabled)
    3. true (re-enable metrics, logs disabled)
    4. true (idempotency, logs disabled)

    This validates:
    - Playbook can deploy with metrics enabled
    - Playbook can disable metrics (logs explicitly set to false)
    - Playbook can re-enable metrics
    - Deployment is idempotent
    - Cleanup works correctly

    Note: logs_enabled is explicitly set to False in all test steps to ensure
    the test validates metrics transitions independently (logs are managed via
    PowerScale API, not by Omnia).

    Note: This is playbook-level validation only. Component-level verification
    (pods, services, configmaps) is covered by FVT tests.
    Note: Logs are managed via PowerScale API, not by Omnia, so only metrics
    transitions are tested here.
    """
    tc_id = "TEL_NFT_POWERSCALE_001"
    tc_title = "Verify PowerScale metrics channel transitions"
    tl = None

    try:
        from library.functions.test_logger import TestLogger
        tl = TestLogger(tc_title, tc_id)
    except Exception:
        tl = None

    try:
        # Step 1: Baseline (metrics enabled)
        _deploy_with_channels(host, tl, True, "Step 1: Baseline", cleanup_first=True)

        # Step 2: Metrics disabled
        _deploy_with_channels(host, tl, False, "Step 2: Metrics disabled", cleanup_first=True)

        # Step 3: Re-enable metrics
        _deploy_with_channels(host, tl, True, "Step 3: Re-enable metrics", cleanup_first=True)

        # Step 4: Idempotency (metrics enabled without cleanup)
        _deploy_with_channels(host, tl, True, "Step 4: Idempotency", cleanup_first=False)

        if tl:
            tl.info("All metrics channel transitions validated successfully")

    except Exception as e:
        if tl:
            tl.error(f"Test failed: {str(e)}")
        raise
