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

"""Repository management functions for OIM prerequisite checks."""

import re
from typing import Dict

from ...core import log as _log
from ..messages.oim_prereq_msgs import OIM_PREREQ_MSGS
from ..vars.oim_prereq_vars import OIM_PREREQ_VARS, OMNIA_TEST_CONFIG_PATH
from .system import run_command, run_shell


def check_rhel_repo() -> Dict:
    """Check if any RHEL repository is configured."""
    _log("Checking RHEL repositories...", "INFO")
    rc, stdout, _ = run_shell("dnf repolist 2>/dev/null")

    if rc == 0 and stdout:
        # Look for common RHEL repo patterns
        repos = []
        for line in stdout.split("\n"):
            line_lower = line.lower()
            if any(x in line_lower for x in ["baseos", "appstream", "rhel", "codeready", "powertools"]):
                repos.append(line.strip())

        if repos:
            return {
                "found": True,
                "repos": repos,
                "message": OIM_PREREQ_MSGS["repo_found"].format(repo=repos[0])
            }

    return {
        "found": False,
        "repos": [],
        "message": "No RHEL repository configured",
        "details": OIM_PREREQ_MSGS["repo_not_found_instruction"]
    }


def check_git() -> Dict:
    """Check if Git is installed."""
    _log("Checking Git installation...", "INFO")
    rc, stdout, _ = run_command(["git", "--version"])

    if rc == 0:
        version_match = re.search(r"(\d+\.\d+\.?\d*)", stdout)
        version = version_match.group(1) if version_match else stdout
        return {
            "installed": True,
            "version": version,
            "message": OIM_PREREQ_MSGS["git_installed"].format(version=version)
        }

    return {
        "installed": False,
        "version": None,
        "message": OIM_PREREQ_MSGS["git_not_installed"]
    }


def install_git() -> Dict:
    """Install Git from RHEL repo if available."""
    # First check if repo is available
    repo_check = check_rhel_repo()
    if not repo_check["found"]:
        return {
            "success": False,
            "message": OIM_PREREQ_MSGS["git_repo_not_found"]
        }

    # Install git
    git_package = OIM_PREREQ_VARS["git_package"]
    rc, _, stderr = run_command(["dnf", "install", "-y", git_package], timeout=120)

    if rc == 0:
        return {
            "success": True,
            "message": OIM_PREREQ_MSGS["git_install_success"]
        }

    return {
        "success": False,
        "message": "Git installation FAILED",
        "error": stderr,
        "details": OIM_PREREQ_MSGS["git_install_instruction"].format(error=stderr, config_path=OMNIA_TEST_CONFIG_PATH)
    }


def ensure_git_installed() -> Dict:
    """Check Git, install if not present."""
    git_check = check_git()

    if git_check["installed"]:
        return git_check

    # Try to install
    install_result = install_git()
    if install_result["success"]:
        # Verify installation
        return check_git()

    return {
        "installed": False,
        "version": None,
        "message": install_result.get("message", "Git installation failed"),
        "details": install_result.get("details", OIM_PREREQ_MSGS["git_install_instruction"].format(error="Unknown error", config_path=OMNIA_TEST_CONFIG_PATH))
    }
