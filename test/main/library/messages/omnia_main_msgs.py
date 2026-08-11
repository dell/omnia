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
Omnia Main — Test Messages

All test names, log messages, assertion messages, and function messages
for the omnia.sh and omnia-cli FVT automation.
"""

from typing import Dict

# =============================================================================
# TEST NAMES (displayed in test output header)
# =============================================================================

TEST_NAMES: Dict[str, str] = {
    # Deploy — setup
    "deploy_setup_venv": (
        "Deploy: omnia.sh --setup-venv --deps-only"
    ),
    "deploy_setup_full": (
        "Deploy: omnia.sh --setup-venv (full setup)"
    ),

    # Deploy — init
    "deploy_init": "Deploy: omnia.sh --init",

    # Setup verification
    "env_file_installed": (
        "Verify omnia.env installed at /etc/omnia/omnia.env"
    ),
    "profile_drop_in": (
        "Verify /etc/profile.d/omnia-env.sh exists"
    ),
    "env_vars_loaded": (
        "Verify environment variables are set after install"
    ),
    "venv_created": (
        "Verify Python venv created at OMNIA_VENV_PATH"
    ),
    "ansible_available": (
        "Verify ansible is available in venv"
    ),
    "base_dirs_created": (
        "Verify base directories created"
    ),
    "activate_helper": (
        "Verify activate-omnia.sh helper script created"
    ),

    # Init verification
    "domain_log_dirs": (
        "Verify domain log directories created"
    ),
    "domain_input_staged": (
        "Verify domain input files staged to data path"
    ),

    # CLI verification
    "help_output": (
        "Verify omnia.sh --help returns usage text"
    ),
    "no_args_shows_help": (
        "Verify omnia.sh with no args shows help"
    ),
    "invalid_domain_error": (
        "Verify --run with invalid domain exits with error"
    ),
    "run_no_domain_error": (
        "Verify --run without domain exits with error"
    ),
    "deps_only_setup": (
        "Verify --deps-only skips input staging"
    ),
    "unknown_option_error": (
        "Verify unknown option exits with error"
    ),

    # Setup — venv content verification
    "pip_packages_installed": (
        "Verify pip packages installed in venv"
    ),
    "galaxy_collections_installed": (
        "Verify Galaxy collections installed in venv"
    ),

    # omnia-cli verification
    "cli_help_output": (
        "Verify omnia-cli help returns usage text"
    ),
    "cli_version_output": (
        "Verify omnia-cli version shows release info"
    ),
    "cli_status_runs": (
        "Verify omnia-cli status runs successfully"
    ),
    "cli_check_runs": (
        "Verify omnia-cli check runs successfully"
    ),
    "cli_status_project_flag": (
        "Verify omnia-cli status --project flag works"
    ),
    "cli_repo_manager": (
        "Verify omnia-cli repo-manager runs"
    ),
    "cli_image_build": (
        "Verify omnia-cli image-build runs"
    ),
    "cli_domain_status": (
        "Verify omnia-cli <domain> runs"
    ),
    "cli_help_domain": (
        "Verify omnia-cli help <domain> runs"
    ),
    "cli_unknown_command": (
        "Verify omnia-cli unknown command exits with error"
    ),
}

# =============================================================================
# TEST LOG MESSAGES
# =============================================================================

TEST_LOG_MSGS: Dict[str, str] = {
    # Setup
    "setup_start": (
        "Running: omnia.sh --setup-venv --deps-only"
    ),
    "setup_success": (
        "Setup completed (rc=0, duration={duration:.1f}s)"
    ),
    "setup_failed": (
        "Setup failed (rc={rc}, duration={duration:.1f}s)"
    ),

    # Init
    "init_start": "Running: omnia.sh --init",
    "init_success": (
        "Init completed (rc=0, duration={duration:.1f}s)"
    ),
    "init_failed": (
        "Init failed (rc={rc}, duration={duration:.1f}s)"
    ),

    # Environment
    "env_file_ok": (
        "omnia.env installed at {path}"
    ),
    "env_file_missing": (
        "omnia.env NOT found at {path}"
    ),
    "profile_ok": (
        "Profile drop-in installed at {path}"
    ),
    "profile_missing": (
        "Profile drop-in NOT found at {path}"
    ),
    "env_vars_ok": (
        "All {count} environment variables are set"
    ),
    "env_vars_missing": (
        "{count} environment variable(s) not set"
    ),

    # Venv
    "venv_ok": "Python venv exists at {path}",
    "venv_missing": "Python venv NOT found at {path}",
    "ansible_ok": "Ansible available: {version}",
    "ansible_missing": "Ansible NOT found in venv",
    "python_ok": "Python available: {version}",

    # Base dirs
    "base_dirs_ok": (
        "All {count} base directories exist"
    ),
    "base_dirs_missing": (
        "{count} base directory(ies) missing"
    ),
    "activate_ok": (
        "activate-omnia.sh exists at {path}"
    ),
    "activate_missing": (
        "activate-omnia.sh NOT found at {path}"
    ),

    # Domain init
    "log_dirs_ok": (
        "All {count} domain log directories exist"
    ),
    "log_dirs_missing": (
        "{count} domain log directory(ies) missing"
    ),
    "input_staged_ok": (
        "Input files staged for {domain}: {count} file(s)"
    ),
    "input_not_staged": (
        "No input files staged for {domain}"
    ),

    # CLI
    "help_ok": "Help output contains expected sections",
    "help_missing_section": (
        "Help output missing section: {section}"
    ),
    "error_exit_ok": (
        "Command exited with expected error (rc={rc})"
    ),
    "error_exit_unexpected": (
        "Command exited with rc={rc}, expected non-zero"
    ),
    "error_msg_ok": (
        "Error message contains: {expected}"
    ),
    "error_msg_missing": (
        "Error message does not mention: {expected}"
    ),

    # Venv content
    "pip_ok": (
        "Pip packages installed: {packages}"
    ),
    "pip_missing": (
        "{count} required pip package(s) not found"
    ),
    "galaxy_ok": (
        "Galaxy collections installed: {count}"
    ),
    "galaxy_missing": (
        "No Galaxy collections found in venv"
    ),

    # omnia-cli
    "cli_help_ok": (
        "omnia-cli help output contains expected sections"
    ),
    "cli_help_missing_section": (
        "omnia-cli help missing section: {section}"
    ),
    "cli_version_ok": (
        "omnia-cli version shows: {version}"
    ),
    "cli_version_missing": (
        "omnia-cli version output missing release info"
    ),
    "cli_status_ok": (
        "omnia-cli status ran successfully"
    ),
    "cli_check_ok": (
        "omnia-cli check ran successfully"
    ),
    "cli_project_ok": (
        "omnia-cli --project flag accepted: {project}"
    ),
    "cli_domain_ok": (
        "omnia-cli {domain} ran (rc={rc})"
    ),
    "cli_domain_help_ok": (
        "omnia-cli help {domain} shows domain info"
    ),
    "cli_unknown_error_ok": (
        "omnia-cli unknown command exited with error (rc={rc})"
    ),
}

# =============================================================================
# TEST ASSERT MESSAGES (user-friendly with HOW TO FIX)
# =============================================================================

_BORDER = "\u2550" * 74

TEST_ASSERT_MSGS: Dict[str, str] = {
    "setup_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 OMNIA SETUP FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Exit code: {rc}\n"
        "\u2551 Duration: {duration:.1f}s\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check that omnia.env has"
        " SYSTEM_ADMIN_NIC_IPV4 set\n"
        "\u2551   2. Verify Python 3.11+ is installed\n"
        "\u2551   3. Check the output above for errors\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "init_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 DOMAIN INIT FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Exit code: {rc}\n"
        "\u2551 Duration: {duration:.1f}s\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run omnia.sh --setup-venv first\n"
        "\u2551   2. Check domain-init.sh scripts exist\n"
        "\u2551   3. Check OMNIA_DATA_PATH is writable\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "env_file_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 ENVIRONMENT FILE NOT INSTALLED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected: {path}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: ./omnia.sh --setup-venv\n"
        "\u2551   2. Check sudo/root permissions\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "profile_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 PROFILE DROP-IN NOT INSTALLED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected: {path}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: ./omnia.sh --setup-venv\n"
        "\u2551   2. Check /etc/profile.d/ is writable\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "env_vars_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 ENVIRONMENT VARIABLES NOT SET\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing:\n"
        "{missing_list}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Source: source /etc/profile.d/"
        "omnia-env.sh\n"
        "\u2551   2. Or: source /opt/omnia/"
        "activate-omnia.sh\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "venv_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 PYTHON VENV NOT FOUND\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected: {path}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: ./omnia.sh --setup-venv\n"
        "\u2551   2. Check Python 3.11+ is installed\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "ansible_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 ANSIBLE NOT AVAILABLE IN VENV\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Venv: {path}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Activate venv and run: pip install"
        " ansible-core\n"
        "\u2551   2. Or re-run: ./omnia.sh --setup-venv\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "base_dirs_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 BASE DIRECTORIES MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing:\n"
        "{missing_list}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: ./omnia.sh --setup-venv\n"
        "\u2551   2. Check OMNIA_DATA_PATH permissions\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "log_dirs_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 DOMAIN LOG DIRECTORIES MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing:\n"
        "{missing_list}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: ./omnia.sh --init\n"
        "\u2551   2. Check /var/log/omnia/ permissions\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "input_not_staged": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 DOMAIN INPUT FILES NOT STAGED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Domain: {domain}\n"
        "\u2551 Expected: {path}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: ./omnia.sh --init\n"
        "\u2551   2. Check domain-init.sh exists\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "help_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 HELP OUTPUT INCOMPLETE\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing section(s): {sections}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check omnia.sh show_help function\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "error_not_raised": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 EXPECTED ERROR NOT RAISED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Command: {command}\n"
        "\u2551 Expected: non-zero exit code\n"
        "\u2551 Got: rc={rc}\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "pip_packages_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 PIP PACKAGES MISSING IN VENV\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing:\n"
        "{missing_list}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: ./omnia.sh --setup-venv\n"
        "\u2551   2. Or activate venv and pip install\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "galaxy_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 GALAXY COLLECTIONS NOT INSTALLED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Venv: {path}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: ./omnia.sh --setup-venv\n"
        "\u2551   2. Or: ansible-galaxy collection install\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "cli_help_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 OMNIA-CLI HELP OUTPUT INCOMPLETE\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing section(s): {sections}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check omnia-cli show_help function\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "cli_version_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 OMNIA-CLI VERSION MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected release string in output\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check omnia-cli OMNIA_RELEASE constant\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "cli_status_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 OMNIA-CLI STATUS FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Exit code: {rc}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run omnia.sh --setup-venv first\n"
        "\u2551   2. Check OMNIA_DATA_PATH is accessible\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
}

# =============================================================================
# FUNCTION MESSAGES (for library functions)
# =============================================================================

OMNIA_MAIN_MSGS: Dict[str, str] = {
    "validation_summary": (
        "\nValidation Summary:\n"
        "- Total: {total}\n"
        "- Passed: {passed}\n"
        "- Failed: {failed}\n"
        "- Skipped: {skipped}\n"
    ),
}
