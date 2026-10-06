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

This test validates playbook-level deployment and status reporting across
metrics_enabled flag variations.

Test Coverage:
- Metrics enable/disable transitions
- Status reporting verification (deployed/disabled/skipped)
- Idempotency verification

Note: This test focuses on playbook-level validation (can we deploy with
different metrics_enabled values and verify the reported status) rather than
component-level verification (which is covered by FVT tests).
Note: Logs are managed via PowerScale API, not by Omnia, so only metrics
transitions are tested here.
"""

import pytest
import yaml

from library.functions import run_playbook
from library.functions.telemetry_func import get_output_path

PLAYBOOK_ENTRY_POINT = "playbooks/telemetry.yml"
PLAYBOOK_WORKDIR = "src/telemetry"
TELEMETRY_STATUS_FILE = "telemetry_status.yml"


def _get_telemetry_status(host):
    """Read telemetry status from the output file.

    Args:
        host: Testinfra host connection to the OIM.

    Returns:
        dict: Parsed telemetry status, or empty dict on failure.
    """
    output_path = get_output_path(host)
    status_path = f"{output_path}/{TELEMETRY_STATUS_FILE}"
    cmd = f"cat {status_path}"
    result = host.run(cmd)
    if result.rc != 0 or not result.stdout.strip():
        return {}
    try:
        return yaml.safe_load(result.stdout) or {}
    except yaml.YAMLError:
        return {}


def _verify_powerscale_status(host, tl, step_name, expected_metrics_status, expected_logs_status):
    """Verify PowerScale status in telemetry_status.yml.

    Args:
        host: Testinfra host connection to the OIM.
        tl: TestLogger instance.
        step_name: Name of the test step.
        expected_metrics_status: Expected metrics status (deployed/disabled/skipped).
        expected_logs_status: Expected logs status (deployed/disabled/skipped).
    """
    status = _get_telemetry_status(host)
    if not status:
        tl.failed(f"[{step_name}] Failed to read telemetry status")
        pytest.fail(f"[{step_name}] Failed to read telemetry status")

    sources = status.get("sources", {})
    powerscale_status = sources.get("powerscale", {})

    actual_metrics = powerscale_status.get("metrics", "unknown")
    actual_logs = powerscale_status.get("logs", "unknown")

    tl.info(f"[{step_name}] PowerScale status: metrics={actual_metrics}, logs={actual_logs}")

    if actual_metrics != expected_metrics_status:
        tl.failed(f"[{step_name}] Expected metrics={expected_metrics_status}, got {actual_metrics}")
        pytest.fail(f"[{step_name}] Metrics status mismatch: expected {expected_metrics_status}, got {actual_metrics}")

    if actual_logs != expected_logs_status:
        tl.failed(f"[{step_name}] Expected logs={expected_logs_status}, got {actual_logs}")
        pytest.fail(f"[{step_name}] Logs status mismatch: expected {expected_logs_status}, got {actual_logs}")

    tl.passed(f"[{step_name}] Status verification passed")


def _deploy_with_channels(host, tl, metrics_enabled, logs_enabled, step_name):
    """Deploy PowerScale with specific metrics/logs configuration.

    Args:
        host: Testinfra host connection to the OIM.
        tl: TestLogger instance.
        metrics_enabled: Boolean for metrics channel.
        logs_enabled: Boolean for logs channel.
        step_name: Name of the test step.
    """
    tl.check(f"[{step_name}] Deploying with metrics={metrics_enabled}, logs={logs_enabled}")

    # Update the telemetry_config.yml file directly
    input_path = "/domain/omnia/telemetry/input/project_default"
    config_file = f"{input_path}/telemetry_config.yml"
    
    # Read current config
    cmd = f"cat {config_file}"
    result = host.run(cmd)
    if result.rc != 0:
        pytest.fail(f"[{step_name}] Failed to read telemetry config")
    
    import yaml
    config = yaml.safe_load(result.stdout)
    
    # Update PowerScale settings
    if "telemetry_sources" not in config:
        config["telemetry_sources"] = {}
    if "powerscale" not in config["telemetry_sources"]:
        config["telemetry_sources"]["powerscale"] = {}
    
    config["telemetry_sources"]["powerscale"]["metrics_enabled"] = metrics_enabled
    config["telemetry_sources"]["powerscale"]["logs_enabled"] = logs_enabled
    
    # Write back
    cmd = f"cat > {config_file} << 'EOF'\n{yaml.dump(config, default_flow_style=False)}EOF"
    result = host.run(cmd)
    if result.rc != 0:
        pytest.fail(f"[{step_name}] Failed to update telemetry config")

    result = run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag="execute",
    )

    if result["rc"] != 0:
        pytest.fail(f"[{step_name}] Deploy failed with exit code {result['rc']}")

    tl.info(f"[{step_name}] Deployment successful")


@pytest.mark.nft
@pytest.mark.source
def test_powerscale_channels_comprehensive(host):
    """Comprehensive test for PowerScale metrics/logs channel transitions.

    Tests the following transitions:
    1. true, true (baseline - metrics enabled, logs enabled)
    2. true, false (metrics enabled, logs disabled)
    3. false, true (metrics disabled, logs enabled)
    4. false, false (metrics disabled, logs disabled - already deployed)
    5. true, true (re-enable both metrics and logs)
    6. true, true (idempotency - same state)

    This validates:
    - Playbook can deploy with metrics and logs enabled
    - Playbook can disable metrics while keeping logs enabled
    - Playbook can disable logs while keeping metrics enabled
    - Playbook can disable both (scale down to 0 replicas)
    - Playbook can re-enable both (scale up from 0 replicas)
    - Deployment is idempotent
    - Status reporting is correct for all transitions

    Note: Logs are managed via PowerScale API, not by Omnia. This test
    validates the status reporting logic, not actual log forwarding.

    Note: This is playbook-level validation only. Component-level verification
    (pods, services, configmaps) is covered by FVT tests.
    """
    tc_id = "TEL_NFT_POWERSCALE_001"
    tc_title = "Verify PowerScale metrics/logs channel transitions"

    from library.functions import TestLogger
    tl = TestLogger(tc_title, tc_id)

    try:
        # Step 1: Baseline (metrics enabled, logs enabled)
        _deploy_with_channels(host, tl, True, True, "Step 1: Baseline (true, true)")
        _verify_powerscale_status(host, tl, "Step 1", "deployed", "deployed")

        # Step 2: Metrics enabled, logs disabled
        _deploy_with_channels(host, tl, True, False, "Step 2: Metrics only (true, false)")
        _verify_powerscale_status(host, tl, "Step 2", "deployed", "disabled")

        # Step 3: Metrics disabled, logs enabled
        _deploy_with_channels(host, tl, False, True, "Step 3: Logs only (false, true)")
        _verify_powerscale_status(host, tl, "Step 3", "disabled", "deployed")

        # Step 4: Both disabled (already deployed)
        _deploy_with_channels(host, tl, False, False, "Step 4: Both disabled (false, false)")
        _verify_powerscale_status(host, tl, "Step 4", "disabled", "disabled")

        # Step 5: Re-enable both
        _deploy_with_channels(host, tl, True, True, "Step 5: Re-enable both (true, true)")
        _verify_powerscale_status(host, tl, "Step 5", "deployed", "deployed")

        # Step 6: Idempotency (same state)
        _deploy_with_channels(host, tl, True, True, "Step 6: Idempotency (true, true)")
        _verify_powerscale_status(host, tl, "Step 6", "deployed", "deployed")

        tl.info("All metrics/logs channel transitions validated successfully")

    except Exception as e:
        tl.fail(f"Test failed: {str(e)}")
        raise
