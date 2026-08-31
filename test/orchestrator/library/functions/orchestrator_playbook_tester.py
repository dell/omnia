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
Orchestrator Playbook Testing Utilities

Functions for testing Ansible playbooks in the orchestrator collection.
Following the deploy/verify pattern from main module testing.
"""

import os
import time
import subprocess
from typing import Any, Dict, Optional

import yaml

from omnia_auto import run_on_host
from library.vars.common_vars import SRC_ORCHESTRATOR_DIR, PLAYBOOK_WORKDIR, CMDS


def check_playbook_exists(playbook_name: str) -> Dict[str, Any]:
    """Check if a playbook exists in the orchestrator playbooks directory.

    Args:
        playbook_name: Name of the playbook to check

    Returns:
        Dict with keys: success, details, error
    """
    playbook_path = os.path.join(SRC_ORCHESTRATOR_DIR, "playbooks", playbook_name)

    if not os.path.exists(playbook_path):
        return {
            "success": False,
            "details": f"Playbook not found: {playbook_path}",
            "error": f"Playbook {playbook_name} does not exist"
        }

    return {
        "success": True,
        "details": f"Playbook exists: {playbook_path}",
        "error": ""
    }


def check_playbook_syntax(playbook_name: str) -> Dict[str, Any]:
    """Validate playbook syntax using ansible-playbook --syntax-check.

    Args:
        playbook_name: Name of the playbook to validate

    Returns:
        Dict with keys: success, details, error
    """
    playbook_path = os.path.join(SRC_ORCHESTRATOR_DIR, "playbooks", playbook_name)

    if not os.path.exists(playbook_path):
        return {
            "success": False,
            "details": f"Playbook not found: {playbook_path}",
            "error": f"Cannot validate syntax - playbook does not exist"
        }

    subprocess.run(
        ["ansible-playbook", "--syntax-check", playbook_path],
        capture_output=True,
        text=True,
        check=True,
        cwd=SRC_ORCHESTRATOR_DIR
    )

    return {
        "success": True,
        "details": f"Playbook {playbook_name} syntax validation passed",
        "error": ""
    }


def get_playbook_tags(playbook_name: str) -> Dict[str, Any]:
    """Get available tags from a playbook.

    Args:
        playbook_name: Name of the playbook to analyze

    Returns:
        Dict with keys: success, details, error, tags
    """
    playbook_path = os.path.join(SRC_ORCHESTRATOR_DIR, "playbooks", playbook_name)

    if not os.path.exists(playbook_path):
        return {
            "success": False,
            "details": f"Playbook not found: {playbook_path}",
            "error": f"Cannot extract tags - playbook does not exist",
            "tags": []
        }

    try:
        with open(playbook_path, 'r', encoding='utf-8') as f:
            playbook_content = yaml.safe_load(f)

        tags = set()
        if not isinstance(playbook_content, list):
            return {
                "success": True,
                "details": f"Found {len(tags)} tag(s) in playbook: {playbook_name}",
                "error": "",
                "tags": sorted(list(tags))
            }

        for play in playbook_content:
            if not isinstance(play, dict):
                continue

            play_tags = play.get("tags", [])
            if isinstance(play_tags, list):
                tags.update(play_tags)
            elif isinstance(play_tags, str):
                tags.add(play_tags)

            # Check tasks for tags
            tasks = play.get("tasks", [])
            for task in tasks:
                if isinstance(task, dict):
                    task_tags = task.get("tags", [])
                    if isinstance(task_tags, list):
                        tags.update(task_tags)
                    elif isinstance(task_tags, str):
                        tags.add(task_tags)

        return {
            "success": True,
            "details": f"Found {len(tags)} tag(s) in playbook: {playbook_name}",
            "error": "",
            "tags": sorted(list(tags))
        }
    except yaml.YAMLError as e:
        return {
            "success": False,
            "details": f"YAML parsing failed",
            "error": f"Invalid YAML in playbook: {str(e)}",
            "tags": []
        }


def deploy_playbook_tag(host, playbook_name: str, tag: str,
                        extra_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Deploy a playbook with a specific tag (deploy phase).

    Args:
        host: Testinfra host connection
        playbook_name: Name of the playbook
        tag: Tag to run
        extra_vars: Optional extra variables

    Returns:
        Dict with keys: success, rc, duration, output, error
    """
    from library.functions import run_playbook

    start_time = time.time()

    result = run_playbook(
        host=host,
        playbook=playbook_name,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag=tag,
        extra_vars=extra_vars
    )

    duration = time.time() - start_time

    if result.get("success"):
        return {
            "success": True,
            "rc": result.get("rc", 0),
            "duration": duration,
            "output": result.get("output", ""),
            "error": ""
        }
    return {
        "success": False,
        "rc": result.get("rc", -1),
        "duration": duration,
        "output": result.get("output", ""),
        "error": result.get("error", "Playbook execution failed")
    }


def verify_playbook_execution(host, playbook_name: str, tag: str) -> Dict[str, Any]:
    """Verify playbook execution results (verify phase).

    Args:
        host: Testinfra host connection
        playbook_name: Name of the playbook that was executed
        tag: Tag that was executed

    Returns:
        Dict with keys: success, details, error
    """
    # Check for playbook execution log
    log_path = f"/opt/omnia/log/core/playbooks/orchestrator_{tag}.log"
    cmd = f"test -f {log_path} && echo exists"
    result = run_on_host(host, cmd)

    if result.rc != 0 or "exists" not in result.stdout:
        return {
            "success": False,
            "details": f"Playbook log not found: {log_path}",
            "error": f"Playbook {playbook_name} with tag {tag} may not have executed"
        }

    # Check log file for errors
    cmd = f"grep -i 'error\\|fail' {log_path} || echo 'no_errors'"
    result = run_on_host(host, cmd)

    if "no_errors" in result.stdout:
        return {
            "success": True,
            "details": f"Playbook {playbook_name} with tag {tag} executed successfully",
            "error": ""
        }
    return {
        "success": False,
        "details": f"Errors found in playbook log: {result.stdout}",
        "error": f"Playbook execution had errors - check {log_path}"
    }


def check_playbook_dependencies(playbook_name: str) -> Dict[str, Any]:
    """Check if playbook dependencies are available.

    Args:
        playbook_name: Name of the playbook to check

    Returns:
        Dict with keys: success, details, error, dependencies
    """
    playbook_path = os.path.join(SRC_ORCHESTRATOR_DIR, "playbooks", playbook_name)

    if not os.path.exists(playbook_path):
        return {
            "success": False,
            "details": f"Playbook not found: {playbook_path}",
            "error": f"Cannot check dependencies - playbook does not exist",
            "dependencies": []
        }

    try:
        with open(playbook_path, 'r', encoding='utf-8') as f:
            playbook_content = yaml.safe_load(f)

        dependencies = []
        if isinstance(playbook_content, list):
            for play in playbook_content:
                if isinstance(play, dict):
                    play_deps = play.get("dependencies", [])
                    dependencies.extend(play_deps)

        # Check if roles exist
        missing_roles = []
        for dep in dependencies:
            if isinstance(dep, dict):
                role_name = dep.get("role", "")
                if role_name and not role_name.startswith("omnia.orchestrator."):
                    # External role - skip for simplicity
                    continue
                elif role_name:
                    # Internal role
                    short_name = role_name.replace("omnia.orchestrator.", "")
                    role_path = f"/root/modern-omnia/omnia/src/orchestrator/roles/{short_name}"
                    if not os.path.exists(role_path):
                        missing_roles.append(role_name)

        if missing_roles:
            return {
                "success": False,
                "details": f"Playbook has missing role dependencies: {missing_roles}",
                "error": f"Missing roles: {missing_roles}",
                "dependencies": dependencies
            }

        return {
            "success": True,
            "details": f"Playbook {playbook_name} dependencies satisfied",
            "error": "",
            "dependencies": dependencies
        }
    except yaml.YAMLError as e:
        return {
            "success": False,
            "details": f"YAML parsing failed",
            "error": f"Invalid YAML in playbook: {str(e)}",
            "dependencies": []
        }


def test_playbook_dry_run(host, playbook_name: str, tag: Optional[str] = None) -> Dict[str, Any]:
    """Test playbook execution with dry-run mode.

    Args:
        host: Testinfra host connection
        playbook_name: Name of the playbook
        tag: Optional tag to run

    Returns:
        Dict with keys: success, details, error
    """
    cmd = CMDS["ansible_playbook"].format(
        workdir=PLAYBOOK_WORKDIR,
        playbook=playbook_name,
        tag=tag if tag else "all"
    )

    # Add --check flag for dry-run
    cmd = cmd.replace("-v", "--check -v")

    result = run_on_host(host, cmd)

    if result.rc == 0:
        return {
            "success": True,
            "details": f"Playbook {playbook_name} dry-run successful",
            "error": ""
        }
    return {
        "success": False,
        "details": f"Dry-run failed: {result.stdout}",
        "error": f"Playbook {playbook_name} dry-run encountered errors"
    }


def measure_playbook_execution_time(host, playbook_name: str, tag: str) -> Dict[str, Any]:
    """Measure playbook execution time for performance testing.

    Args:
        host: Testinfra host connection
        playbook_name: Name of the playbook
        tag: Tag to run

    Returns:
        Dict with keys: success, duration, details, error
    """
    start_time = time.time()

    result = deploy_playbook_tag(host, playbook_name, tag)

    duration = time.time() - start_time

    return {
        "success": result["success"],
        "duration": duration,
        "details": f"Playbook {playbook_name} with tag {tag} took {duration:.2f}s",
        "error": result.get("error", "")
    }
