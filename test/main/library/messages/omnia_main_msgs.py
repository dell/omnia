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
    "domain_output_dirs": (
        "Verify domain output directories created"
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

    # Init verification — domain input staging (per domain)
    "domain_input_staged_orchestrator": (
        "Verify domain input files staged for orchestrator"
    ),
    "domain_input_staged_discovery": (
        "Verify domain input files staged for discovery"
    ),

    # CLI verification — --cleanup / --check-deps / --force-deps
    "cleanup_in_help": (
        "Verify --cleanup flag appears in help output"
    ),
    "check_deps_in_help": (
        "Verify --check-deps flag appears in help output"
    ),
    "force_deps_in_help": (
        "Verify --force-deps flag appears in help output"
    ),
    "skip_catalog_in_help": (
        "Verify --skip-catalog flag appears in help output"
    ),
    "skip_omnia_cli_in_help": (
        "Verify --skip-omnia-cli flag appears in help output"
    ),

    # Init domain filtering
    "init_domain_filter": (
        "Verify --init <domain> filters to specific domains"
    ),

    # Check deps
    "check_deps_runs": (
        "Verify --check-deps runs successfully"
    ),
    "force_deps_invalid": (
        "Verify --force-deps without -s/-i exits with error"
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

    # omnia-cli logs verification
    "cli_logs_help": (
        "Verify omnia-cli logs --help runs"
    ),
    "cli_logs_limit": (
        "Verify omnia-cli logs --limit flag works"
    ),
    "cli_logs_limit_invalid": (
        "Verify omnia-cli logs --limit rejects invalid values"
    ),
    "cli_logs_limit_short": (
        "Verify omnia-cli logs -l short form works"
    ),

    # omnia.sh tags verification
    "sh_generic_tags_in_help": (
        "Verify omnia.sh help shows generic tags (precheck, validate, prepare, execute, cleanup)"
    ),
    "sh_tags_run": (
        "Verify omnia.sh --run <domain> --tags <tag> accepts generic tags"
    ),

    # omnia-cli remaining domain status
    "cli_orchestrator": (
        "Verify omnia-cli orchestrator runs"
    ),
    "cli_telemetry": (
        "Verify omnia-cli telemetry runs"
    ),
    "cli_build_stream": (
        "Verify omnia-cli build-stream runs"
    ),

    # Setup — env source validation
    "env_source_validation": (
        "Verify env validation rejects missing SYSTEM_ADMIN_NIC_IPV4"
    ),
    "env_source_update": (
        "Verify updated omnia.env propagates to /etc/omnia/omnia.env"
    ),

    # CLI — skip-catalog / skip-omnia-cli
    "skip_catalog_accepted": (
        "Verify --setup-venv --skip-catalog accepted"
    ),
    "skip_omnia_cli_accepted": (
        "Verify --setup-venv --skip-omnia-cli accepted"
    ),

    # CLI — --skip / --dry-run
    "skip_in_help": (
        "Verify --skip flag appears in help output"
    ),
    "dry_run_in_help": (
        "Verify --dry-run flag appears in help output"
    ),
    "skip_invalid_domain": (
        "Verify --skip with invalid domain exits with error"
    ),
    "skip_with_include_error": (
        "Verify --skip + explicit domain list is rejected"
    ),
    "skip_without_init_error": (
        "Verify --skip without -s/-i exits with error"
    ),
    "skip_no_args_error": (
        "Verify --skip without domain list exits with error"
    ),
    "dry_run_output": (
        "Verify --dry-run shows domain list without executing"
    ),
    "dry_run_with_skip": (
        "Verify --dry-run --skip shows filtered domain list"
    ),
    "dry_run_without_init_error": (
        "Verify --dry-run without -s/-i exits with error"
    ),
    # --prepare-base CLI verification
    "prepare_base_in_help": (
        "Verify --prepare-base flag appears in help output"
    ),
    "prepare_base_dry_run_output": (
        "Verify --prepare-base --dry-run shows domains and phases"
    ),
    "prepare_base_dry_run_skip": (
        "Verify --prepare-base --dry-run --skip filters domains"
    ),
    "prepare_base_skip_invalid": (
        "Verify --prepare-base --skip with invalid domain exits with error"
    ),
    "prepare_base_skip_all": (
        "Verify --prepare-base --skip all domains shows no-op message"
    ),
    "prepare_base_dry_run_phases": (
        "Verify --prepare-base --dry-run shows all lifecycle phases"
    ),
    "prepare_base_dry_run_fail_fast_note": (
        "Verify --prepare-base --dry-run shows fail-fast note"
    ),
    "prepare_base_dry_run_domain_order": (
        "Verify --prepare-base --dry-run shows correct domain order"
    ),
    "prepare_base_dry_run_skip_multiple": (
        "Verify --prepare-base --dry-run --skip with 2 domains"
    ),

    # Execution — actual omnia.sh operations
    "exec_setup_full": (
        "Execute omnia.sh --setup-venv (full setup)"
    ),
    "exec_init_domain": (
        "Execute omnia.sh --init for single domain"
    ),
    "exec_run_validate": (
        "Execute omnia.sh --run with --tags validate"
    ),
    "exec_run_precheck": (
        "Execute omnia.sh --run with --tags precheck"
    ),
    "exec_cleanup": (
        "Execute omnia.sh --cleanup"
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
    "output_dirs_ok": (
        "All {count} domain output directories exist"
    ),
    "output_dirs_missing": (
        "{count} domain output directory(ies) missing"
    ),
    "input_staged_ok": (
        "Input files staged for {domain}: {count} file(s)"
    ),
    "input_not_staged": (
        "No input files staged for {domain}"
    ),

    # Cleanup / check-deps / force-deps CLI
    "cleanup_in_help_ok": (
        "--cleanup flag found in help output"
    ),
    "cleanup_not_in_help": (
        "--cleanup flag NOT found in help output"
    ),
    "check_deps_in_help_ok": (
        "--check-deps flag found in help output"
    ),
    "check_deps_not_in_help": (
        "--check-deps flag NOT found in help output"
    ),
    "force_deps_in_help_ok": (
        "--force-deps flag found in help output"
    ),
    "force_deps_not_in_help": (
        "--force-deps flag NOT found in help output"
    ),
    "skip_catalog_in_help_ok": (
        "--skip-catalog flag found in help output"
    ),
    "skip_catalog_not_in_help": (
        "--skip-catalog flag NOT found in help output"
    ),
    "skip_omnia_cli_in_help_ok": (
        "--skip-omnia-cli flag found in help output"
    ),
    "skip_omnia_cli_not_in_help": (
        "--skip-omnia-cli flag NOT found in help output"
    ),
    "check_deps_ok": (
        "--check-deps completed successfully"
    ),
    "check_deps_failed": (
        "--check-deps failed (rc={rc})"
    ),
    "init_domain_ok": (
        "Domain-filtered init completed for {domain}"
    ),
    "init_domain_failed": (
        "Domain-filtered init failed for {domain} (rc={rc})"
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

    # omnia-cli logs
    "cli_logs_help_ok": (
        "omnia-cli logs --help ran successfully"
    ),
    "cli_logs_help_failed": (
        "omnia-cli logs --help failed"
    ),
    "cli_logs_limit_ok": (
        "omnia-cli logs --limit {limit} accepted"
    ),
    "cli_logs_limit_invalid_ok": (
        "omnia-cli logs --limit {limit} rejected (rc={rc})"
    ),
    "cli_logs_limit_short_ok": (
        "omnia-cli logs -l {limit} accepted"
    ),

    # omnia.sh tags
    "sh_generic_tags_ok": (
        "Help shows all 5 generic tags per domain"
    ),
    "sh_generic_tags_missing": (
        "Help missing generic tags: {missing}"
    ),

    # omnia-cli remaining domains
    "cli_orchestrator_ok": (
        "omnia-cli orchestrator ran (rc={rc})"
    ),
    "cli_telemetry_ok": (
        "omnia-cli telemetry ran (rc={rc})"
    ),
    "cli_build_stream_ok": (
        "omnia-cli build-stream ran (rc={rc})"
    ),

    # Env source validation
    "env_source_validation_ok": (
        "validate_env_source correctly rejected "
        "missing SYSTEM_ADMIN_NIC_IPV4"
    ),
    "env_source_validation_failed": (
        "validate_env_source did NOT reject "
        "missing SYSTEM_ADMIN_NIC_IPV4 (rc={rc})"
    ),

    # Env update propagation
    "env_update_ok": (
        "Source omnia.env update propagated to system copy"
    ),
    "env_update_failed": (
        "Source omnia.env update did NOT propagate to system copy"
    ),

    # --skip / --dry-run
    "skip_in_help_ok": (
        "--skip flag found in help output"
    ),
    "skip_not_in_help": (
        "--skip flag NOT found in help output"
    ),
    "dry_run_in_help_ok": (
        "--dry-run flag found in help output"
    ),
    "dry_run_not_in_help": (
        "--dry-run flag NOT found in help output"
    ),
    "skip_invalid_ok": (
        "--skip with invalid domain exited with error (rc={rc})"
    ),
    "skip_include_error_ok": (
        "--skip + explicit domain rejected (rc={rc})"
    ),
    "skip_without_init_ok": (
        "--skip without -s/-i rejected (rc={rc})"
    ),
    "skip_no_args_ok": (
        "--skip without domain list rejected (rc={rc})"
    ),
    "dry_run_ok": (
        "--dry-run listed domains without executing"
    ),
    "dry_run_skip_ok": (
        "--dry-run --skip listed filtered domains"
    ),
    "dry_run_without_init_ok": (
        "--dry-run without -s/-i rejected (rc={rc})"
    ),
    # skip-catalog / skip-omnia-cli
    "skip_catalog_ok": (
        "--setup-venv --skip-catalog completed (rc={rc})"
    ),
    "skip_catalog_failed": (
        "--setup-venv --skip-catalog failed (rc={rc})"
    ),
    "skip_omnia_cli_ok": (
        "--setup-venv --skip-omnia-cli completed (rc={rc})"
    ),
    "skip_omnia_cli_failed": (
        "--setup-venv --skip-omnia-cli failed (rc={rc})"
    ),

    # --prepare-base
    "prepare_base_in_help_ok": (
        "--prepare-base flag found in help output"
    ),
    "prepare_base_not_in_help": (
        "--prepare-base flag NOT found in help output"
    ),
    "prepare_base_dry_run_ok": (
        "--prepare-base --dry-run listed domains and phases"
    ),
    "prepare_base_dry_run_failed": (
        "--prepare-base --dry-run output missing expected content"
    ),
    "prepare_base_dry_run_skip_ok": (
        "--prepare-base --dry-run --skip listed filtered domains"
    ),
    "prepare_base_skip_invalid_ok": (
        "--prepare-base --skip invalid domain rejected (rc={rc})"
    ),
    "prepare_base_skip_all_ok": (
        "--prepare-base --skip all domains showed no-op message"
    ),
    "prepare_base_skip_all_failed": (
        "--prepare-base --skip all domains did not show no-op message"
    ),
    "prepare_base_phases_ok": (
        "--prepare-base --dry-run shows all lifecycle phases"
    ),
    "prepare_base_phases_missing": (
        "--prepare-base --dry-run missing phases: {missing}"
    ),
    "prepare_base_fail_fast_ok": (
        "--prepare-base --dry-run shows fail-fast note"
    ),
    "prepare_base_fail_fast_missing": (
        "--prepare-base --dry-run missing fail-fast note"
    ),
    "prepare_base_order_ok": (
        "--prepare-base --dry-run shows correct domain order"
    ),
    "prepare_base_order_wrong": (
        "--prepare-base --dry-run domain order incorrect"
    ),

    # Execution — actual operations
    "exec_setup_ok": (
        "Full setup completed (rc={rc}, duration={duration:.1f}s)"
    ),
    "exec_setup_failed": (
        "Full setup failed (rc={rc}, duration={duration:.1f}s)"
    ),
    "exec_init_domain_ok": (
        "--init {domain} completed (rc={rc}, duration={duration:.1f}s)"
    ),
    "exec_init_domain_failed": (
        "--init {domain} failed (rc={rc}, duration={duration:.1f}s)"
    ),
    "exec_run_ok": (
        "--run {domain} --tags {tag} completed (rc={rc}, duration={duration:.1f}s)"
    ),
    "exec_run_failed": (
        "--run {domain} --tags {tag} failed (rc={rc}, duration={duration:.1f}s)"
    ),
    "exec_cleanup_ok": (
        "--cleanup completed (rc={rc})"
    ),
    "exec_cleanup_failed": (
        "--cleanup failed (rc={rc})"
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

    "output_dirs_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 DOMAIN OUTPUT DIRECTORIES MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing:\n"
        "{missing_list}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: ./omnia.sh --init\n"
        "\u2551   2. Check OMNIA_DATA_PATH permissions\n"
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

    "cleanup_not_in_help": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --CLEANUP FLAG MISSING FROM HELP\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected '--cleanup' to appear in omnia.sh --help\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Add --cleanup to omnia.sh show_help()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "check_deps_not_in_help": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --CHECK-DEPS FLAG MISSING FROM HELP\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected '--check-deps' to appear in omnia.sh --help\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Add --check-deps to omnia.sh show_help()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "force_deps_not_in_help": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --FORCE-DEPS FLAG MISSING FROM HELP\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected '--force-deps' to appear in omnia.sh --help\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Add --force-deps to omnia.sh show_help()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "skip_catalog_not_in_help": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --SKIP-CATALOG FLAG MISSING FROM HELP\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected '--skip-catalog' to appear in omnia.sh --help\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Add --skip-catalog to omnia.sh show_help()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "check_deps_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --CHECK-DEPS COMMAND FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Exit code: {rc}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check that domain requirements files exist\n"
        "\u2551   2. Align versions across domains\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "force_deps_invalid": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --FORCE-DEPS USED WITHOUT -S/-I\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 --force-deps requires --setup-venv or --init\n"
        "\u2551 Got: rc={rc}\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "env_source_validation_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 ENV SOURCE VALIDATION DID NOT REJECT BAD INPUT\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 validate_env_source should exit non-zero when\n"
        "\u2551 SYSTEM_ADMIN_NIC_IPV4 is missing or invalid.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check validate_env_source() in omnia.sh\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "skip_catalog_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --SKIP-CATALOG NOT ACCEPTED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 omnia.sh --setup-venv --skip-catalog should be\n"
        "\u2551 accepted without error (rc={rc}).\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check --skip-catalog parsing in omnia.sh main()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "skip_omnia_cli_not_in_help": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --SKIP-OMNIA-CLI FLAG MISSING FROM HELP\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected '--skip-omnia-cli' to appear in omnia.sh --help\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Add --skip-omnia-cli to omnia.sh show_help()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "skip_omnia_cli_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --SKIP-OMNIA-CLI NOT ACCEPTED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 omnia.sh --setup-venv --skip-omnia-cli should be\n"
        "\u2551 accepted without error (rc={rc}).\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check --skip-omnia-cli parsing in omnia.sh main()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    # --skip / --dry-run
    "skip_not_in_help": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --SKIP FLAG MISSING FROM HELP\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected '--skip' to appear in omnia.sh --help\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Add --skip to omnia.sh show_help()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "dry_run_not_in_help": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --DRY-RUN FLAG MISSING FROM HELP\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected '--dry-run' to appear in omnia.sh --help\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Add --dry-run to omnia.sh show_help()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "skip_invalid_domain": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --SKIP WITH INVALID DOMAIN NOT REJECTED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 --skip nonexistent_domain_xyz should exit non-zero\n"
        "\u2551 Got: rc={rc}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check skip domain validation in init_domains()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "skip_with_include": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --SKIP + EXPLICIT DOMAIN NOT REJECTED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 --init telemetry --skip utils should exit non-zero\n"
        "\u2551 Got: rc={rc}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check mutual exclusion validation in main()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "skip_without_init": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --SKIP WITHOUT -S/-I NOT REJECTED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 --skip without --init or --setup-venv should exit non-zero\n"
        "\u2551 Got: rc={rc}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check flag combination validation in main()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "skip_no_args": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --SKIP WITHOUT DOMAIN LIST NOT REJECTED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 --skip without a domain list should exit non-zero\n"
        "\u2551 Got: rc={rc}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check --skip argument parsing in main()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "dry_run_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --DRY-RUN DID NOT SHOW DOMAIN LIST\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 --dry-run should print domain list without executing\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check dry-run logic in init_domains()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "dry_run_without_init": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --DRY-RUN WITHOUT -I/-S NOT REJECTED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 --dry-run without --init or --setup-venv should exit non-zero\n"
        "\u2551 Got: rc={rc}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check flag combination validation in main()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    # --prepare-base
    "prepare_base_not_in_help": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --PREPARE-BASE FLAG MISSING FROM HELP\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected '--prepare-base' to appear in omnia.sh --help\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Add --prepare-base to omnia.sh show_help()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "prepare_base_dry_run_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --PREPARE-BASE --DRY-RUN DID NOT SHOW EXPECTED OUTPUT\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 --prepare-base --dry-run should print DRY RUN header\n"
        "\u2551 and list base domains (repo_manager, image_build_manager,\n"
        "\u2551 orchestrator)\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check dry-run logic in prepare_base_domains()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "prepare_base_skip_invalid": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --PREPARE-BASE --SKIP INVALID DOMAIN NOT REJECTED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 --prepare-base --skip nonexistent_domain_xyz should\n"
        "\u2551 exit non-zero. Got: rc={rc}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check skip validation in prepare_base_domains()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "prepare_base_skip_all_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --PREPARE-BASE --SKIP ALL DID NOT SHOW NO-OP\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Skipping all 3 domains should show a no-op message.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check empty-array guard in prepare_base_domains()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "prepare_base_phases_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --PREPARE-BASE --DRY-RUN MISSING LIFECYCLE PHASES\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected phases: validate, credentials, prepare\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check LIFECYCLE_TAGS in omnia.sh\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "prepare_base_fail_fast_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --PREPARE-BASE --DRY-RUN MISSING FAIL-FAST NOTE\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected note about fail-fast execution model.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check dry-run output in prepare_base_domains()\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "prepare_base_order_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 --PREPARE-BASE DOMAIN ORDER INCORRECT\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Expected order: repo_manager, image_build_manager,\n"
        "\u2551 orchestrator.\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check PREPARE_ORDER in omnia.sh\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    # Execution tests
    "exec_setup_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 FULL SETUP EXECUTION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 omnia.sh --setup-venv failed (rc={rc}).\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check omnia.env has valid SYSTEM_ADMIN_NIC_IPV4\n"
        "\u2551   2. Verify Python >= 3.11 is installed\n"
        "\u2551   3. Check domain-init.sh scripts exist\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "exec_init_domain_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 DOMAIN INIT EXECUTION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 omnia.sh --init {domain} failed (rc={rc}).\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check domain-init.sh exists for {domain}\n"
        "\u2551   2. Verify venv is set up first (omnia.sh -s)\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "exec_run_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 DOMAIN RUN EXECUTION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 omnia.sh --run {domain} --tags {tag} failed (rc={rc}).\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Verify venv + domain init completed\n"
        "\u2551   2. Check domain playbook supports --tags {tag}\n"
        "\u2551   3. Review ansible-playbook output for errors\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
    "exec_cleanup_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 CLEANUP EXECUTION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 omnia.sh --cleanup failed (rc={rc}).\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check cleanup_omnia() in omnia.sh\n"
        "\u2551   2. Verify file permissions on /etc/omnia/, /etc/profile.d/\n"
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
