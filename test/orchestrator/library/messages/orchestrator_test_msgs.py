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
Orchestrator Testing Framework Messages

Test names, log messages, and assertion messages for the new
orchestrator testing utilities (modules, roles, playbooks).
"""

from typing import Dict

# =============================================================================
# TEST NAMES
# =============================================================================
TEST_NAMES: Dict[str, str] = {
    # Module testing
    "module_validation": "Validate module: {module_name}",
    "module_import": "Test module import: {module_name}",
    "module_schema": "Test module schema validation: {module_name}",
    "module_dependencies": "Check module dependencies: {module_name}",

    # Role testing
    "role_structure": "Check role structure: {role_name}",
    "role_tasks": "Check role tasks: {role_name}",
    "role_vars": "Check role variables: {role_name}",
    "role_metadata": "Check role metadata: {role_name}",
    "role_dependencies": "Test role dependencies: {role_name}",
    "role_syntax": "Validate role syntax: {role_name}",

    # Playbook testing
    "playbook_exists": "Check playbook exists: {playbook_name}",
    "playbook_syntax": "Validate playbook syntax: {playbook_name}",
    "playbook_tags": "Get playbook tags: {playbook_name}",
    "playbook_deploy": "Deploy playbook: {playbook_name} --tags {tag}",
    "playbook_verify": "Verify playbook execution: {playbook_name} --tags {tag}",
    "playbook_dependencies": "Check playbook dependencies: {playbook_name}",
    "playbook_dry_run": "Test playbook dry-run: {playbook_name}",
    "playbook_performance": "Measure playbook execution time: {playbook_name}",
}

# =============================================================================
# TEST LOG MESSAGES
# =============================================================================
TEST_LOG_MSGS: Dict[str, str] = {
    # Module testing
    "module_validation_ok": "Module {module_name} validation passed",
    "module_validation_failed": "Module {module_name} validation failed",
    "module_import_ok": "Module {module_name} imported successfully",
    "module_import_failed": "Module {module_name} import failed",
    "module_schema_ok": "Module {module_name} schema validation passed",
    "module_schema_failed": "Module {module_name} schema validation failed",
    "module_deps_ok": "All dependencies available for module {module_name}",
    "module_deps_missing": "Module {module_name} has missing dependencies: {deps}",

    # Role testing
    "role_structure_ok": "Role {role_name} structure is valid",
    "role_structure_failed": "Role {role_name} structure is invalid",
    "role_tasks_ok": "Role {role_name} has valid tasks",
    "role_tasks_failed": "Role {role_name} has invalid or missing tasks",
    "role_vars_ok": "Role {role_name} has valid variables",
    "role_vars_failed": "Role {role_name} has invalid variables",
    "role_metadata_ok": "Role {role_name} has valid metadata",
    "role_metadata_failed": "Role {role_name} has invalid metadata",
    "role_deps_ok": "Role {role_name} dependencies satisfied",
    "role_deps_failed": "Role {role_name} has missing dependencies: {deps}",
    "role_syntax_ok": "Role {role_name} syntax validation passed",
    "role_syntax_failed": "Role {role_name} syntax validation failed",

    # Playbook testing
    "playbook_exists_ok": "Playbook {playbook_name} exists",
    "playbook_exists_failed": "Playbook {playbook_name} not found",
    "playbook_syntax_ok": "Playbook {playbook_name} syntax validation passed",
    "playbook_syntax_failed": "Playbook {playbook_name} syntax validation failed",
    "playbook_tags_ok": "Playbook {playbook_name} has {count} tag(s): {tags}",
    "playbook_deploy_ok": "Playbook {playbook_name} deployed successfully",
    "playbook_deploy_failed": "Playbook {playbook_name} deployment failed",
    "playbook_verify_ok": "Playbook {playbook_name} execution verified",
    "playbook_verify_failed": "Playbook {playbook_name} execution verification failed",
    "playbook_deps_ok": "Playbook {playbook_name} dependencies satisfied",
    "playbook_deps_failed": "Playbook {playbook_name} has missing dependencies",
    "playbook_dry_run_ok": "Playbook {playbook_name} dry-run successful",
    "playbook_dry_run_failed": "Playbook {playbook_name} dry-run failed",
    "playbook_performance_ok": "Playbook {playbook_name} execution time: {duration:.2f}s",
    "playbook_performance_failed": "Playbook {playbook_name} performance test failed",
}

# =============================================================================
# TEST ASSERTION MESSAGES
# =============================================================================
_BORDER = "\u2550" * 74

TEST_ASSERT_MSGS: Dict[str, str] = {
    # Module testing
    "module_validation_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 MODULE VALIDATION FAILED: {module_name}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check module file exists: src/orchestrator/plugins/modules/{module_name}.py\n"
        "\u2551   2. Verify module syntax and imports\n"
        "\u2551   3. Check module dependencies are installed\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "module_import_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 MODULE IMPORT FAILED: {module_name}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check Python path and module location\n"
        "\u2551   2. Verify ansible-core is installed\n"
        "\u2551   3. Check for missing dependencies\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    # Role testing
    "role_structure_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 ROLE STRUCTURE INVALID: {role_name}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing directories: {missing_dirs}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Create missing directories in src/orchestrator/roles/{role_name}/\n"
        "\u2551   2. Ensure at minimum 'tasks' directory exists\n"
        "\u2551   3. Add main.yml to tasks directory\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "role_tasks_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 ROLE TASKS INVALID: {role_name}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Ensure tasks/main.yml exists\n"
        "\u2551   2. Validate YAML syntax in task files\n"
        "\u2551   3. Check for proper task structure\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "role_deps_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 ROLE DEPENDENCIES FAILED: {role_name}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing dependencies: {deps}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Install missing role dependencies\n"
        "\u2551   2. Update meta/main.yml with correct dependency names\n"
        "\u2551   3. Run: ansible-galaxy install -r requirements.yml\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    # Playbook testing
    "playbook_syntax_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 PLAYBOOK SYNTAX FAILED: {playbook_name}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Validate YAML syntax in playbook\n"
        "\u2551   2. Check for proper indentation and structure\n"
        "\u2551   3. Run: ansible-playbook --syntax-check {playbook_name}\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "playbook_deploy_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 PLAYBOOK DEPLOYMENT FAILED: {playbook_name}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Tag: {tag}\n"
        "\u2551 Exit code: {rc}\n"
        "\u2551 Duration: {duration:.1f}s\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check playbook output above for errors\n"
        "\u2551   2. Verify orchestrator_config.yml settings\n"
        "\u2551   3. Run with increased verbosity: -vvv\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "playbook_verify_failed": (
        "\u2554" + _BORDER + "\u2557\n"
        "\u2551 PLAYBOOK VERIFICATION FAILED: {playbook_name}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Error: {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check playbook execution logs\n"
        "\u2551   2. Verify playbook actually completed\n"
        "\u2551   3. Review log file: /opt/omnia/log/core/playbooks/orchestrator_{tag}.log\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
}
