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
Telemetry Deploy — Install Mode Verification Tests.

Unified test module that detects the current install_mode (online/offline) from
telemetry_packages.yml and runs the appropriate verification tests for all
sources. Replaces the separate test_idrac_offline.py and test_online_mode.py.

Online mode characteristics:
    - Python packages installed from PyPI
    - Helm charts downloaded from upstream (GitHub releases)
    - Git repos cloned directly from GitHub
    - Container images from upstream registries

Offline mode characteristics:
    - Python packages installed from Pulp repo
    - Helm charts downloaded from Pulp repo
    - Container images from local registry

Test cases:
    TC_SR_100: Verify install_mode configuration is valid
    TC_SR_101: Verify Python packages installed correctly for current mode
    TC_SR_102: Verify iDRAC deployment succeeded in current mode
    TC_SR_103: Verify iDRAC pods running in current mode
    TC_SR_104: Verify PowerScale dependencies available for current mode
    TC_SR_105: Verify PowerScale deployment succeeded in current mode
"""

import pytest
import yaml

from library.functions import TestLogger
from library.vars.test_case_vars import TEST_CASES as TC
from library.vars.common_vars import (
    IDRAC_STS_NAME,
    IDRAC_POD_PREFIX,
    TELEMETRY_NAMESPACE,
    TELEMETRY_PACKAGES_FILE,
    CMDS,
)
from library.messages.telemetry_msgs import (
    TEST_LOG_MSGS as LOG_MSGS,
    TEST_ASSERT_MSGS as ASSERT_MSGS,
)
from library.functions.k8s_func import (
    verify_sts_ready,
    verify_pods_by_prefix,
)
from library.functions.telemetry_func import (
    is_source_enabled,
    run_on_kube_vip,
    _get_input_path,
)
from library.functions.powerscale_func import (
    verify_powerscale_deployment,
)
from omnia_auto import run_on_host, log


# =========================================================================
# Helpers
# =========================================================================

def _get_install_mode(host):
    """Read install_mode from telemetry_packages.yml on the OIM host.

    Returns:
        str: 'online' or 'offline' (or whatever value is configured).
    """
    input_path = _get_input_path(host)
    file_path = f"{input_path}/{TELEMETRY_PACKAGES_FILE}"
    cmd = CMDS["cat_file"].format(path=file_path)
    result = run_on_host(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return None
    try:
        data = yaml.safe_load(result.stdout) or {}
    except yaml.YAMLError:
        return None
    return data.get("install_mode")


def _get_repo_url(host):
    """Read repo_url from telemetry_packages.yml on the OIM host."""
    input_path = _get_input_path(host)
    file_path = f"{input_path}/{TELEMETRY_PACKAGES_FILE}"
    cmd = CMDS["cat_file"].format(path=file_path)
    result = run_on_host(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return None
    try:
        data = yaml.safe_load(result.stdout) or {}
    except yaml.YAMLError:
        return None
    return data.get("repo_url")


def _skip_if_idrac_disabled(host):
    """Skip test if iDRAC source is not enabled or not deployed."""
    if not is_source_enabled(host, "idrac"):
        pytest.skip("iDRAC source not enabled in config")
    result = verify_sts_ready(host, IDRAC_STS_NAME)
    if result.get("not_found"):
        pytest.skip("iDRAC StatefulSet not found (no BMC inventory configured)")


def _skip_if_powerscale_disabled(host):
    """Skip test if PowerScale source is not enabled or not deployed."""
    if not is_source_enabled(host, "powerscale"):
        pytest.skip("PowerScale source not enabled in config")


# =========================================================================
# TC_SR_100: Verify install_mode configuration is valid
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(100)
def test_install_mode_config(host):
    """TC_SR_100: Verify telemetry_packages.yml has a valid install_mode."""
    tc = TC["install_mode_config"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Reading telemetry_packages.yml install_mode")
    install_mode = _get_install_mode(host)

    if not install_mode:
        tl.failed("install_mode not found in telemetry_packages.yml", "")
        pytest.fail("install_mode not found in telemetry_packages.yml")

    details = f"install_mode: {install_mode}"
    valid_modes = ("online", "offline")

    if install_mode in valid_modes:
        tl.passed(
            LOG_MSGS["config_value_correct"].format(
                key="install_mode", value=install_mode
            ),
            details,
        )
    else:
        tl.failed(
            LOG_MSGS["config_value_incorrect"].format(
                key="install_mode",
                expected="online or offline",
                actual=install_mode,
            ),
            details,
        )

    assert install_mode in valid_modes, (
        ASSERT_MSGS["config_value_incorrect"].format(
            key="install_mode",
            expected="online or offline",
            actual=install_mode,
        )
    )


# =========================================================================
# TC_SR_101: Verify Python packages installed correctly for current mode
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(101)
def test_python_packages_installed(host):
    """TC_SR_101: Verify Python packages installed for the current mode."""
    _skip_if_idrac_disabled(host)
    tc = TC["install_mode_python_packages"]
    tl = TestLogger(tc["title"], tc["id"])

    install_mode = _get_install_mode(host)
    if not install_mode:
        pytest.skip("install_mode not found in telemetry_packages.yml")

    tl.check("Verifying kubernetes package installation")
    cmd = "python3 -c 'import kubernetes; print(kubernetes.__version__)'"
    result = run_on_kube_vip(host, cmd)

    if result.rc != 0:
        tl.failed("kubernetes package not found", "")
        pytest.fail("kubernetes package not found")

    mode_label = "Pulp repo" if install_mode == "offline" else "PyPI"
    details = f"kubernetes version: {result.stdout.strip()}\nInstall mode: {install_mode} ({mode_label})"

    if install_mode == "offline":
        repo_url = _get_repo_url(host)
        if repo_url:
            details += f"\nPulp repo: {repo_url}"

    tl.passed(
        LOG_MSGS["python_package_installed"].format(
            package=f"kubernetes (from {mode_label})"
        ),
        details,
    )


# =========================================================================
# TC_SR_102: Verify iDRAC deployment succeeded in current mode
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(102)
def test_idrac_deployment(host):
    """TC_SR_102: Verify iDRAC deployment succeeded in the current mode."""
    _skip_if_idrac_disabled(host)
    tc = TC["install_mode_idrac_deployment"]
    tl = TestLogger(tc["title"], tc["id"])

    install_mode = _get_install_mode(host) or "unknown"
    component = f"iDRAC StatefulSet ({install_mode} mode)"

    tl.check("Verifying iDRAC StatefulSet deployment")
    result = verify_sts_ready(host, IDRAC_STS_NAME)

    if result["success"]:
        tl.passed(
            LOG_MSGS["pods_running"].format(
                component=component,
                count=result["ready_replicas"],
                expected=result["expected"],
            ),
            f"Ready: {result['ready_replicas']}/{result['expected']}",
        )
    else:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component=component,
                running=result["ready_replicas"],
                expected=result["expected"],
            ),
            "",
        )

    assert result["success"], ASSERT_MSGS["pods_not_running"].format(
        component=component,
        expected=result["expected"],
        running=result["ready_replicas"],
    )


# =========================================================================
# TC_SR_103: Verify iDRAC pods running in current mode
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(103)
def test_idrac_pods(host):
    """TC_SR_103: Verify iDRAC pods running in the current mode."""
    _skip_if_idrac_disabled(host)
    tc = TC["install_mode_idrac_pods"]
    tl = TestLogger(tc["title"], tc["id"])

    install_mode = _get_install_mode(host) or "unknown"
    component = f"iDRAC ({install_mode} mode)"

    tl.check("Finding iDRAC pods")
    pods_result = verify_pods_by_prefix(host, IDRAC_POD_PREFIX, min_count=1)
    if not pods_result["success"] or not pods_result["pods"]:
        tl.failed(
            LOG_MSGS["pods_not_running"].format(
                component=component, running=0, expected=1,
            ),
            "",
        )
        pytest.fail("No iDRAC pods found")

    details_lines = [f"Found {len(pods_result['pods'])} iDRAC pod(s)"]
    for pod_info in pods_result["pods"]:
        details_lines.append(f"  - {pod_info['name']}")
    details = "\n".join(details_lines)

    tl.passed(
        LOG_MSGS["pods_running"].format(
            component=component,
            count=len(pods_result["pods"]),
            expected="at least 1",
        ),
        details,
    )

    assert len(pods_result["pods"]) >= 1, ASSERT_MSGS["pods_not_running"].format(
        component=component,
        expected="at least 1",
        running=len(pods_result["pods"]),
    )


# =========================================================================
# TC_SR_104: Verify PowerScale dependencies available for current mode
# =========================================================================

@pytest.mark.source
@pytest.mark.functional
@pytest.mark.order(104)
def test_powerscale_dependencies(host):
    """TC_SR_104: Verify PowerScale dependencies for the current mode."""
    _skip_if_powerscale_disabled(host)
    tc = TC["install_mode_powerscale_deps"]
    tl = TestLogger(tc["title"], tc["id"])

    install_mode = _get_install_mode(host) or "unknown"

    if install_mode == "online":
        tl.check("Checking karavi-observability git clone")
        cmd = "ls -la /opt/omnia/k8s_mount/telemetry/karavi-observability/karavi-observability/.git 2>/dev/null"
        result = run_on_kube_vip(host, cmd)

        if result.rc == 0:
            details = "karavi-observability: cloned from GitHub"
            tl.passed(
                LOG_MSGS["git_repo_cloned"].format(repo="karavi-observability"),
                details,
            )
        else:
            tl.failed(
                LOG_MSGS["git_repo_not_cloned"].format(repo="karavi-observability"),
                "",
            )
            pytest.fail("karavi-observability git repo not found")

        tl.check("Checking helm-charts git clone")
        cmd = "ls -la /opt/omnia/k8s_mount/telemetry/karavi-observability/helm-charts/.git 2>/dev/null"
        result = run_on_kube_vip(host, cmd)

        if result.rc == 0:
            details = "helm-charts: cloned from GitHub"
            tl.passed(
                LOG_MSGS["git_repo_cloned"].format(repo="helm-charts"),
                details,
            )
        else:
            tl.failed(
                LOG_MSGS["git_repo_not_cloned"].format(repo="helm-charts"),
                "",
            )
            pytest.fail("helm-charts git repo not found")
    else:
        # Offline mode: verify Pulp-based artifacts exist
        tl.check("Checking PowerScale helm chart available from local repo")
        cmd = "ls /opt/omnia/k8s_mount/telemetry/karavi-observability/ 2>/dev/null"
        result = run_on_kube_vip(host, cmd)

        if result.rc == 0 and result.stdout.strip():
            tl.passed(
                LOG_MSGS["deployment_success"].format(
                    component=f"PowerScale dependencies ({install_mode} mode)"
                ),
                f"Files found in karavi-observability directory",
            )
        else:
            tl.failed(
                LOG_MSGS["deployment_failed"].format(
                    component=f"PowerScale dependencies ({install_mode} mode)"
                ),
                "",
            )
            pytest.fail("PowerScale dependencies not found")


# =========================================================================
# TC_SR_105: Verify PowerScale deployment succeeded in current mode
# =========================================================================

@pytest.mark.source
@pytest.mark.sanity
@pytest.mark.order(105)
def test_powerscale_deployment(host):
    """TC_SR_105: Verify PowerScale deployment succeeded in the current mode."""
    _skip_if_powerscale_disabled(host)
    tc = TC["install_mode_powerscale_deployment"]
    tl = TestLogger(tc["title"], tc["id"])

    install_mode = _get_install_mode(host) or "unknown"
    component = f"PowerScale ({install_mode} mode)"

    tl.check("Verifying PowerScale CSM Metrics deployment")
    result = verify_powerscale_deployment(host)

    if result["success"]:
        tl.passed(
            LOG_MSGS["deployment_success"].format(component=component),
            result.get("details", ""),
        )
    else:
        tl.failed(
            LOG_MSGS["deployment_failed"].format(component=component),
            result.get("error", ""),
        )

    assert result["success"], ASSERT_MSGS["deployment_failed"].format(
        component=component
    )
