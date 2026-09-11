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
Orchestrator Cleanup — Verification Tests.

ORCH_FVT_CLEANUP_V001: Verify containers removed after cleanup
ORCH_FVT_CLEANUP_V002: Verify services stopped after cleanup
ORCH_FVT_CLEANUP_V003: Verify firewall ports closed after cleanup
"""

import pytest

from library.functions import (
    TestLogger,
    check_containers_removed,
    check_services_removed,
    check_firewall_ports_closed,
    load_test_config,
)
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
)


pytestmark = pytest.mark.destructive


@pytest.mark.sanity
@pytest.mark.order(1)
def test_containers_removed(host):
    """ORCH_FVT_CLEANUP_V001: Verify containers removed after cleanup."""
    tl = TestLogger(TEST_NAMES["containers_removed"], "ORCH_FVT_CLEANUP_V001")
    result = check_containers_removed(host)

    if result["success"]:
        tl.passed(LOG["container_running"].format(
            container="none (all removed)"
        ), result["details"])
    else:
        tl.failed(
            LOG["container_not_running"].format(container="cleanup"),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.sanity
@pytest.mark.order(2)
def test_services_removed(host):
    """ORCH_FVT_CLEANUP_V002: Verify services stopped after cleanup."""
    tl = TestLogger(TEST_NAMES["services_removed"], "ORCH_FVT_CLEANUP_V002")
    result = check_services_removed(host)

    if result["success"]:
        tl.passed(LOG["services_removed_ok"], result["details"])
    else:
        tl.failed(
            LOG["services_still_active"].format(count=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.order(3)
def test_firewall_ports_closed(host):
    """ORCH_FVT_CLEANUP_V003: Verify firewall ports closed after cleanup."""
    tl = TestLogger(TEST_NAMES["firewall_ports_closed"], "ORCH_FVT_CLEANUP_V003")
    result = check_firewall_ports_closed(host)

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["firewall_ports_closed_ok"], result["details"])
    else:
        tl.failed(
            LOG["firewall_ports_still_open"].format(count=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


def _project_paths():
    """Resolve target paths from the same settings used by the runner."""
    config = load_test_config()
    shared_path = config.get("shared_path", "/opt/omnia/orchestrator").rstrip("/")
    project = config.get("project_name", "project_default")
    return {
        "input": f"{shared_path}/input/{project}",
        "output": f"{shared_path}/output/{project}",
    }


@pytest.mark.sanity
@pytest.mark.order(4)
def test_cleanup_preserves_project_input(host):
    """ORCH_FVT_CLEANUP_V004: Default cleanup preserves required project input files."""
    input_path = _project_paths()["input"]
    required = ("omnia_config.yml", "orchestrator_config.yml", "network_spec.yml")
    missing = [name for name in required if not host.file(f"{input_path}/{name}").is_file]
    assert not missing, f"Cleanup removed required project inputs: {missing}"


@pytest.mark.sanity
@pytest.mark.order(5)
def test_cleanup_preserves_credentials_by_default(host):
    """ORCH_FVT_CLEANUP_V005: Plain cleanup does not remove opt-in credential files."""
    input_path = _project_paths()["input"]
    required = (
        "omnia_config_credentials.yml",
        ".omnia_config_credentials_key",
    )
    missing = [name for name in required if not host.file(f"{input_path}/{name}").is_file]
    assert not missing, (
        "Plain cleanup removed credential files without cleanup_credentials: "
        f"{missing}"
    )


@pytest.mark.functional
@pytest.mark.order(6)
def test_cleanup_removes_project_output(host):
    """ORCH_FVT_CLEANUP_V006: Cleanup removes Orchestrator deployment output."""
    output_path = _project_paths()["output"]
    assert not host.file(output_path).exists, (
        f"Orchestrator output remains after cleanup: {output_path}"
    )


@pytest.mark.functional
@pytest.mark.order(7)
def test_cleanup_removes_framework_state(host):
    """ORCH_FVT_CLEANUP_V007: Cleanup removes its transient log and state directories."""
    shared_path = load_test_config().get(
        "shared_path", "/opt/omnia/orchestrator"
    ).rstrip("/")
    data_path = shared_path.rsplit("/orchestrator", 1)[0]
    stale = [
        path for path in (
            f"{data_path}/orchestrator/log/cleanup",
            "/var/lib/omnia/cleanup",
        )
        if host.file(path).exists
    ]
    assert not stale, f"Cleanup framework artifacts remain: {stale}"
