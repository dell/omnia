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
Build Stream — GitLab Cleanup Verification Functions.

Functions to verify that GitLab packages, the runner container, quadlet,
services, directories and port are removed from the GitLab server after
running the cleanup playbook.
"""

from typing import Any, Dict, List

from library.functions.gitlab_ssh_func import (
    get_gitlab_config,
    gitlab_package_installed,
    gitlab_service_state,
    probe_gitlab_url,
    ssh_to_gitlab,
)
from library.functions.probe_func import Probe, summarize_probes
from library.vars.common_vars import (
    CMDS,
    GITLAB_CLEANUP_DIRECTORIES,
    GITLAB_INSTALLED_PACKAGES,
    GITLAB_RUNNER_CONTAINER,
    GITLAB_RUNNER_QUADLET_DIR,
    GITLAB_RUNNER_QUADLET_FILE,
    GITLAB_RUNNER_SERVICES,
    GITLAB_SERVICES,
)

# Shown when the GitLab server cannot be reached over SSH after cleanup.
_UNREACHABLE = "GitLab server not reachable over SSH (expected once it is removed)"


# =========================================================================
# SECTION C: GitLab Cleanup Verification
# =========================================================================
# Every check prints one line per package, container, file, unit, directory
# or port it inspected, with a check or cross mark.

def _unreachable(label: str) -> List[Probe]:
    """Return the passing probe used when SSH to the GitLab server fails."""
    return [(label, _UNREACHABLE, True)]


def check_gitlab_packages_removed(host) -> Dict[str, Any]:
    """Verify every GitLab package is removed from the GitLab server.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    probes = []
    for package in GITLAB_INSTALLED_PACKAGES:
        installed = gitlab_package_installed(host, package)
        probes.append((f"Package {package}", "STILL INSTALLED" if installed else "removed",
                       not installed))
    return summarize_probes("gitlab_packages", probes)


def check_gitlab_runner_container_removed(host) -> Dict[str, Any]:
    """Verify the gitlab-runner container is removed from the GitLab server.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    label = f"Container {GITLAB_RUNNER_CONTAINER}"
    listing = ssh_to_gitlab(host, CMDS["gitlab_container_names"])
    if not listing["success"]:
        return summarize_probes("gitlab_runner_container", _unreachable(label))
    present = GITLAB_RUNNER_CONTAINER in listing.get("stdout", "").split()
    return summarize_probes("gitlab_runner_container", [
        (label, "STILL EXISTS" if present else "removed", not present)])


def check_gitlab_runner_quadlet_removed(host) -> Dict[str, Any]:
    """Verify the gitlab-runner quadlet file is removed.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    path = f"{GITLAB_RUNNER_QUADLET_DIR}/{GITLAB_RUNNER_QUADLET_FILE}"
    probe = ssh_to_gitlab(host, CMDS["gitlab_path_state"].format(path=path))
    if not probe["success"]:
        return summarize_probes("gitlab_runner_quadlet", _unreachable(f"Quadlet {path}"))
    present = probe.get("stdout", "").strip() == "exists"
    return summarize_probes("gitlab_runner_quadlet", [
        (f"Quadlet {path}", "STILL EXISTS" if present else "removed", not present)])


def check_gitlab_runner_services_stopped(host) -> Dict[str, Any]:
    """Verify every GitLab runner systemd service is stopped.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    probes = []
    for service in GITLAB_RUNNER_SERVICES:
        state = gitlab_service_state(host, service["name"], "inactive")
        probes.append((f"Unit {service['name']}",
                       "STILL ACTIVE" if state == "active" else state, state != "active"))
    return summarize_probes("gitlab_runner_services", probes)


def check_gitlab_url_not_accessible(host) -> Dict[str, Any]:
    """Verify the GitLab URL no longer answers after cleanup.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    probe = probe_gitlab_url(host)
    if not probe["host"]:
        return summarize_probes("gitlab_url", [
            ("gitlab_host", "not set (cleanup complete)", True)])
    answers = probe["http_code"] in (200, 302)
    state = (f"STILL ACCESSIBLE (HTTP {probe['http_code']})" if answers
             else f"not accessible (HTTP {probe['http_code']})")
    return summarize_probes("gitlab_url", [(f"URL {probe['url']}", state, not answers)])


def check_gitlab_directories_removed(host) -> Dict[str, Any]:
    """Verify every GitLab directory is removed from the GitLab server.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    probes = []
    for path in GITLAB_CLEANUP_DIRECTORIES:
        probe = ssh_to_gitlab(host, CMDS["gitlab_path_state"].format(path=path))
        if not probe["success"]:
            probes.extend(_unreachable(f"Directory {path}"))
            continue
        present = probe.get("stdout", "").strip() == "exists"
        probes.append((f"Directory {path}", "STILL EXISTS" if present else "removed",
                       not present))
    return summarize_probes("gitlab_directories", probes)


def check_gitlab_services_stopped(host) -> Dict[str, Any]:
    """Verify no GitLab service still runs according to ``gitlab-ctl status``.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    status = ssh_to_gitlab(host, CMDS["gitlab_ctl_status"])
    if not status["success"]:
        return summarize_probes("gitlab_services", [
            ("gitlab-ctl", "not available (expected after uninstall)", True)])
    lines = status.get("stdout", "").splitlines()
    probes = []
    for service in GITLAB_SERVICES:
        running = any(line.startswith("run:") and service in line for line in lines)
        probes.append((f"Service {service}", "STILL RUNNING" if running else "stopped",
                       not running))
    return summarize_probes("gitlab_services", probes)


def check_gitlab_port_free(host) -> Dict[str, Any]:
    """Verify the GitLab HTTPS port is free after cleanup.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    port = get_gitlab_config(host).get("gitlab_https_port", "443")
    label = f"TCP port {port}"
    listening = ssh_to_gitlab(host, CMDS["ss_port_check"].format(port=port))
    if not listening["success"]:
        return summarize_probes("gitlab_port", _unreachable(label))
    output = listening.get("stdout", "").strip()
    return summarize_probes("gitlab_port", [
        (label, f"STILL IN USE ({output})" if output else "free", not output)])
