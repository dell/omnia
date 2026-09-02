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
Orchestrator Role Testing Utilities

Functions for testing Ansible roles in the orchestrator collection.
Following the same pattern as main module testing.
"""

import os
from typing import Any, Dict, List

from omnia_auto import load_test_config, run_on_host
from ..vars.common_vars import SRC_ORCHESTRATOR_DIR


def check_role_structure(role_name: str) -> Dict[str, Any]:
    """Check if an orchestrator role has proper structure.

    Args:
        role_name: Name of the role to check

    Returns:
        Dict with keys: success, details, error, missing_dirs
    """
    role_path = os.path.join(SRC_ORCHESTRATOR_DIR, "roles", role_name)

    if not os.path.exists(role_path):
        return {
            "success": False,
            "details": f"Role directory not found: {role_path}",
            "error": f"Role {role_name} does not exist",
            "missing_dirs": []
        }

    # Standard Ansible role directories
    required_dirs = ["tasks", "vars", "defaults", "meta", "handlers"]
    optional_dirs = ["templates", "files", "library", "module_utils"]

    missing_dirs = []
    existing_dirs = []

    for dir_name in required_dirs:
        dir_path = os.path.join(role_path, dir_name)
        if os.path.exists(dir_path):
            existing_dirs.append(dir_name)
        else:
            missing_dirs.append(dir_name)

    # Check for at least tasks directory (most critical)
    if "tasks" not in existing_dirs:
        return {
            "success": False,
            "details": f"Role missing critical 'tasks' directory",
            "error": f"Role {role_name} must have a tasks directory",
            "missing_dirs": missing_dirs
        }

    return {
        "success": True,
        "details": f"Role {role_name} structure valid. Has: {existing_dirs}",
        "error": "",
        "missing_dirs": missing_dirs
    }


def check_role_tasks(role_name: str) -> Dict[str, Any]:
    """Check if role has valid task files.

    Args:
        role_name: Name of the role to check

    Returns:
        Dict with keys: success, details, error, task_files
    """
    role_path = os.path.join(SRC_ORCHESTRATOR_DIR, "roles", role_name)
    tasks_dir = os.path.join(role_path, "tasks")

    if not os.path.exists(tasks_dir):
        return {
            "success": False,
            "details": f"Tasks directory not found: {tasks_dir}",
            "error": f"Role {role_name} has no tasks directory",
            "task_files": []
        }

    task_files = []
    for file in os.listdir(tasks_dir):
        if file.endswith(".yml") or file.endswith(".yaml"):
            task_files.append(file)

    if not task_files:
        return {
            "success": False,
            "details": f"No task files found in {tasks_dir}",
            "error": f"Role {role_name} must have at least one task file",
            "task_files": []
        }

    # Check for main.yml (standard entry point)
    if "main.yml" not in task_files and "main.yaml" not in task_files:
        return {
            "success": False,
            "details": f"Task files found: {task_files}, but missing main.yml",
            "error": f"Role {role_name} should have main.yml as entry point",
            "task_files": task_files
        }

    return {
        "success": True,
        "details": f"Role {role_name} has {len(task_files)} task file(s): {task_files}",
        "error": "",
        "task_files": task_files
    }


def check_role_vars(role_name: str) -> Dict[str, Any]:
    """Check if role has valid variable files.

    Args:
        role_name: Name of the role to check

    Returns:
        Dict with keys: success, details, error, var_files
    """
    role_path = os.path.join(SRC_ORCHESTRATOR_DIR, "roles", role_name)
    vars_dir = os.path.join(role_path, "vars")

    if not os.path.exists(vars_dir):
        # Vars directory is optional
        return {
            "success": True,
            "details": f"Role {role_name} has no vars directory (optional)",
            "error": "",
            "var_files": []
        }

    var_files = []
    for file in os.listdir(vars_dir):
        if file.endswith(".yml") or file.endswith(".yaml"):
            var_files.append(file)

    return {
        "success": True,
        "details": f"Role {role_name} has {len(var_files)} var file(s): {var_files}",
        "error": "",
        "var_files": var_files
    }


def check_role_defaults(role_name: str) -> Dict[str, Any]:
    """Check if role has valid defaults file.

    Args:
        role_name: Name of the role to check

    Returns:
        Dict with keys: success, details, error
    """
    role_path = os.path.join(SRC_ORCHESTRATOR_DIR, "roles", role_name)
    defaults_dir = os.path.join(role_path, "defaults")

    if not os.path.exists(defaults_dir):
        # Defaults directory is optional
        return {
            "success": True,
            "details": f"Role {role_name} has no defaults directory (optional)",
            "error": ""
        }

    main_defaults = os.path.join(defaults_dir, "main.yml")
    if os.path.exists(main_defaults):
        return {
            "success": True,
            "details": f"Role {role_name} has defaults/main.yml",
            "error": ""
        }

    return {
        "success": True,
        "details": f"Role {role_name} has defaults directory but no main.yml",
        "error": ""
    }


def check_role_metadata(role_name: str) -> Dict[str, Any]:
    """Check if role has valid metadata.

    Args:
        role_name: Name of the role to check

    Returns:
        Dict with keys: success, details, error, metadata
    """
    role_path = os.path.join(SRC_ORCHESTRATOR_DIR, "roles", role_name)
    meta_dir = os.path.join(role_path, "meta")
    main_yml = os.path.join(meta_dir, "main.yml")

    if not os.path.exists(main_yml):
        return {
            "success": False,
            "details": f"Role metadata not found: {main_yml}",
            "error": f"Role {role_name} should have meta/main.yml",
            "metadata": {}
        }

    try:
        import yaml
        with open(main_yml, 'r') as f:
            metadata = yaml.safe_load(f) or {}

        # Handle galaxy_info structure
        galaxy_info = metadata.get("galaxy_info", {})

        # Check for required metadata fields
        required_fields = ["author", "description"]
        missing_fields = [field for field in required_fields if field not in galaxy_info]

        if missing_fields:
            return {
                "success": False,
                "details": f"Role metadata missing required fields: {missing_fields}",
                "error": f"Role metadata must contain: {required_fields}",
                "metadata": galaxy_info
            }

        return {
            "success": True,
            "details": f"Role {role_name} has valid metadata",
            "error": "",
            "metadata": galaxy_info
        }
    except yaml.YAMLError as e:
        return {
            "success": False,
            "details": f"Role metadata YAML parsing failed",
            "error": f"Invalid YAML in meta/main.yml: {str(e)}",
            "metadata": {}
        }


def test_role_dependencies(role_name: str, host) -> Dict[str, Any]:
    """Test if role dependencies can be satisfied.

    Args:
        role_name: Name of the role to test
        host: Testinfra host connection

    Returns:
        Dict with keys: success, details, error, dependencies
    """
    role_path = os.path.join(SRC_ORCHESTRATOR_DIR, "roles", role_name)
    meta_main = os.path.join(role_path, "meta", "main.yml")

    if not os.path.exists(meta_main):
        return {
            "success": True,
            "details": f"Role {role_name} has no dependencies (no meta/main.yml)",
            "error": "",
            "dependencies": []
        }

    try:
        import yaml
        with open(meta_main, 'r') as f:
            metadata = yaml.safe_load(f) or {}

        dependencies = metadata.get("dependencies", [])

        if not dependencies:
            return {
                "success": True,
                "details": f"Role {role_name} has no dependencies defined",
                "error": "",
                "dependencies": []
            }

        # Check if dependencies are available
        missing_deps = []
        for dep in dependencies:
            if isinstance(dep, dict):
                dep_name = dep.get("role", dep.get("name", str(dep)))
            else:
                dep_name = str(dep)

            # Simple check - assume local roles are in the same collection
            dep_path = os.path.join(SRC_ORCHESTRATOR_DIR, "roles", dep_name)
            if not os.path.exists(dep_path):
                missing_deps.append(dep_name)

        if missing_deps:
            return {
                "success": False,
                "details": f"Role {role_name} has missing dependencies: {missing_deps}",
                "error": f"Missing role dependencies: {missing_deps}",
                "dependencies": dependencies
            }

        return {
            "success": True,
            "details": f"Role {role_name} dependencies satisfied: {len(dependencies)} dep(s)",
            "error": "",
            "dependencies": dependencies
        }
    except yaml.YAMLError as e:
        return {
            "success": False,
            "details": f"Role metadata YAML parsing failed",
            "error": f"Invalid YAML in meta/main.yml: {str(e)}",
            "dependencies": []
        }


def validate_role_syntax(role_name: str) -> Dict[str, Any]:
    """Validate role YAML syntax using ansible-playbook --syntax-check.

    Args:
        role_name: Name of the role to validate

    Returns:
        Dict with keys: success, details, error
    """
    role_path = os.path.join(SRC_ORCHESTRATOR_DIR, "roles", role_name)

    # Create a temporary playbook to test the role
    test_playbook_content = f"""
---
- name: Test role syntax
  hosts: localhost
  roles:
    - {role_path}
"""

    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write(test_playbook_content)
        temp_playbook = f.name

    try:
        # Run ansible-playbook syntax check
        import subprocess
        result = subprocess.run(
            ["ansible-playbook", "--syntax-check", temp_playbook],
            capture_output=True,
            text=True,
            cwd=SRC_ORCHESTRATOR_DIR
        )

        if result.returncode == 0:
            return {
                "success": True,
                "details": f"Role {role_name} syntax validation passed",
                "error": ""
            }
        else:
            return {
                "success": False,
                "details": f"Syntax check failed: {result.stderr}",
                "error": f"Role {role_name} has syntax errors"
            }
    finally:
        os.unlink(temp_playbook)
