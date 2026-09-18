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

"""Omnia Main test-case registry.

Central registry mapping every FVT and NFT test function to its stable test
case ID and user-facing title.
"""

TEST_CASES = {
    # -- CLI --
    "no_args_shows_help": {
        "id": "MAIN_FVT_CLI_V001",
        "title": 'Verify omnia.sh with no args shows help',
    },
    "run_invalid_domain": {
        "id": "MAIN_FVT_CLI_V002",
        "title": 'Verify --run with invalid domain exits with error',
    },
    "run_no_domain": {
        "id": "MAIN_FVT_CLI_V003",
        "title": 'Verify --run without domain exits with error',
    },
    "deps_only_in_help": {
        "id": "MAIN_FVT_CLI_V004",
        "title": 'Verify --deps-only skips input staging',
    },
    "unknown_option": {
        "id": "MAIN_FVT_CLI_V005",
        "title": 'Verify unknown option exits with error',
    },
    "cleanup_in_help": {
        "id": "MAIN_FVT_CLI_V006",
        "title": 'Verify --cleanup flag appears in help output',
    },
    "check_deps_in_help": {
        "id": "MAIN_FVT_CLI_V007",
        "title": 'Verify --check-deps flag appears in help output',
    },
    "force_deps_in_help": {
        "id": "MAIN_FVT_CLI_V008",
        "title": 'Verify --force-deps flag appears in help output',
    },
    "skip_catalog_in_help": {
        "id": "MAIN_FVT_CLI_V009",
        "title": 'Verify --skip-catalog flag appears in help output',
    },
    "force_deps_invalid": {
        "id": "MAIN_FVT_CLI_V010",
        "title": 'Verify --force-deps without -s/-i exits with error',
    },
    "check_deps_runs": {
        "id": "MAIN_FVT_CLI_V011",
        "title": 'Verify --check-deps runs successfully',
    },
    "skip_catalog_accepted": {
        "id": "MAIN_FVT_CLI_V012",
        "title": 'Verify --setup-venv --skip-catalog accepted',
    },
    "skip_omnia_cli_in_help": {
        "id": "MAIN_FVT_CLI_V013",
        "title": 'Verify --skip-omnia-cli flag appears in help output',
    },
    "skip_omnia_cli_accepted": {
        "id": "MAIN_FVT_CLI_V014",
        "title": 'Verify --setup-venv --skip-omnia-cli accepted',
    },
    "skip_in_help": {
        "id": "MAIN_FVT_CLI_V015",
        "title": 'Verify --skip flag appears in help output',
    },
    "dry_run_in_help": {
        "id": "MAIN_FVT_CLI_V016",
        "title": 'Verify --dry-run flag appears in help output',
    },
    "skip_invalid_domain": {
        "id": "MAIN_FVT_CLI_V017",
        "title": 'Verify --skip with invalid domain exits with error',
    },
    "skip_with_include_error": {
        "id": "MAIN_FVT_CLI_V018",
        "title": 'Verify --skip + explicit domain list is rejected',
    },
    "skip_without_init_error": {
        "id": "MAIN_FVT_CLI_V019",
        "title": 'Verify --skip without -s/-i exits with error',
    },
    "skip_no_args_error": {
        "id": "MAIN_FVT_CLI_V020",
        "title": 'Verify --skip without domain list exits with error',
    },
    "dry_run_output": {
        "id": "MAIN_FVT_CLI_V021",
        "title": 'Verify --dry-run shows domain list without executing',
    },
    "dry_run_with_skip": {
        "id": "MAIN_FVT_CLI_V022",
        "title": 'Verify --dry-run --skip shows filtered domain list',
    },
    "dry_run_without_init_error": {
        "id": "MAIN_FVT_CLI_V023",
        "title": 'Verify --dry-run without -s/-i exits with error',
    },
    "prepare_base_in_help": {
        "id": "MAIN_FVT_CLI_V024",
        "title": 'Verify --prepare-base flag appears in help output',
    },
    "prepare_base_dry_run": {
        "id": "MAIN_FVT_CLI_V025",
        "title": 'Verify --prepare-base --dry-run shows domains and phases',
    },
    "prepare_base_dry_run_skip": {
        "id": "MAIN_FVT_CLI_V026",
        "title": 'Verify --prepare-base --dry-run --skip filters domains',
    },
    "prepare_base_skip_invalid": {
        "id": "MAIN_FVT_CLI_V027",
        "title": 'Verify --prepare-base --skip with invalid domain exits with error',
    },
    "prepare_base_skip_all": {
        "id": "MAIN_FVT_CLI_V028",
        "title": 'Verify --prepare-base --skip all domains shows no-op message',
    },
    "prepare_base_dry_run_phases": {
        "id": "MAIN_FVT_CLI_V029",
        "title": 'Verify --prepare-base --dry-run shows all lifecycle phases',
    },
    "prepare_base_dry_run_fail_fast_note": {
        "id": "MAIN_FVT_CLI_V030",
        "title": 'Verify --prepare-base --dry-run shows fail-fast note',
    },
    "prepare_base_dry_run_domain_order": {
        "id": "MAIN_FVT_CLI_V031",
        "title": 'Verify --prepare-base --dry-run shows correct domain order',
    },
    "prepare_base_dry_run_skip_multiple": {
        "id": "MAIN_FVT_CLI_V032",
        "title": 'Verify --prepare-base --dry-run --skip with 2 domains',
    },
    "generic_tags_in_help": {
        "id": "MAIN_FVT_CLI_V033",
        "title": (
            'Verify omnia.sh help shows generic tags '
            '(precheck, validate, prepare, execute, cleanup)'
        ),
    },
    "execution_order_in_help": {
        "id": "MAIN_FVT_CLI_V034",
        "title": 'Verify execution order in help',
    },
    "help_output": {
        "id": "MAIN_FVT_CLI_E001",
        "title": 'Verify omnia.sh --help returns usage text',
    },
    # -- EXECUTION --
    "verify_venv_exists": {
        "id": "MAIN_FVT_EXECUTION_V001",
        "title": 'Verify venv and Ansible after setup',
    },
    "verify_env_installed": {
        "id": "MAIN_FVT_EXECUTION_V002",
        "title": 'Verify environment files after setup',
    },
    "verify_domain_log_dirs": {
        "id": "MAIN_FVT_EXECUTION_V003",
        "title": 'Verify domain log directories after init',
    },
    "verify_domain_input_staged": {
        "id": "MAIN_FVT_EXECUTION_V004",
        "title": 'Verify domain inputs after init',
    },
    "deploy_setup_deps_only": {
        "id": "MAIN_FVT_EXECUTION_E001",
        "title": 'Execute omnia.sh --setup-venv (full setup)',
    },
    "deploy_init_domain": {
        "id": "MAIN_FVT_EXECUTION_E002",
        "title": 'Execute omnia.sh --init for single domain',
    },
    "deploy_run_precheck": {
        "id": "MAIN_FVT_EXECUTION_E003",
        "title": 'Execute omnia.sh --run with --tags precheck',
    },
    "deploy_run_validate": {
        "id": "MAIN_FVT_EXECUTION_E004",
        "title": 'Execute omnia.sh --run with --tags validate',
    },
    # -- CLEANUP --
    "deploy_cleanup": {
        "id": "MAIN_FVT_CLEANUP_E001",
        "title": 'Execute omnia.sh --cleanup',
    },
    # -- INIT --
    "domain_log_dirs": {
        "id": "MAIN_FVT_INIT_V001",
        "title": 'Verify domain log directories created',
    },
    "domain_output_dirs": {
        "id": "MAIN_FVT_INIT_V002",
        "title": 'Verify domain output directories created',
    },
    "domain_input_staged_image_build_manager": {
        "id": "MAIN_FVT_INIT_V003",
        "title": 'Verify domain input files staged to data path',
    },
    "domain_input_staged_repo_manager": {
        "id": "MAIN_FVT_INIT_V004",
        "title": 'Verify domain input files staged to data path',
    },
    "domain_input_staged_orchestrator": {
        "id": "MAIN_FVT_INIT_V005",
        "title": 'Verify domain input files staged for orchestrator',
    },
    "domain_input_staged_discovery": {
        "id": "MAIN_FVT_INIT_V006",
        "title": 'Verify domain input files staged for discovery',
    },
    "init_domain_filter": {
        "id": "MAIN_FVT_INIT_V007",
        "title": 'Verify --init <domain> filters to specific domains',
    },
    "init_force_deps": {
        "id": "MAIN_FVT_INIT_V008",
        "title": 'Verify --init --force-deps forces dep reinstall',
    },
    "deploy_init": {
        "id": "MAIN_FVT_INIT_E001",
        "title": 'Deploy: omnia.sh --init',
    },
    # -- OMNIA_CLI --
    "cli_status_runs": {
        "id": "MAIN_FVT_OMNIA_CLI_V001",
        "title": 'Verify omnia-cli status runs successfully',
    },
    "cli_check_runs": {
        "id": "MAIN_FVT_OMNIA_CLI_V002",
        "title": 'Verify omnia-cli check runs successfully',
    },
    "cli_status_project_flag": {
        "id": "MAIN_FVT_OMNIA_CLI_V003",
        "title": 'Verify omnia-cli status --project flag works',
    },
    "cli_repo_manager": {
        "id": "MAIN_FVT_OMNIA_CLI_V004",
        "title": 'Verify omnia-cli repo-manager runs',
    },
    "cli_image_build": {
        "id": "MAIN_FVT_OMNIA_CLI_V005",
        "title": 'Verify omnia-cli image-build runs',
    },
    "cli_discovery_status": {
        "id": "MAIN_FVT_OMNIA_CLI_V006",
        "title": 'Verify omnia-cli <domain> runs',
    },
    "cli_help_repo_manager": {
        "id": "MAIN_FVT_OMNIA_CLI_V007",
        "title": 'Verify omnia-cli help <domain> runs',
    },
    "cli_help_discovery": {
        "id": "MAIN_FVT_OMNIA_CLI_V008",
        "title": 'Verify omnia-cli help <domain> runs',
    },
    "cli_orchestrator": {
        "id": "MAIN_FVT_OMNIA_CLI_V009",
        "title": 'Verify omnia-cli orchestrator runs',
    },
    "cli_telemetry": {
        "id": "MAIN_FVT_OMNIA_CLI_V010",
        "title": 'Verify omnia-cli telemetry runs',
    },
    "cli_build_stream": {
        "id": "MAIN_FVT_OMNIA_CLI_V011",
        "title": 'Verify omnia-cli build-stream runs',
    },
    "cli_unknown_command": {
        "id": "MAIN_FVT_OMNIA_CLI_V012",
        "title": 'Verify omnia-cli unknown command exits with error',
    },
    "cli_logs_help": {
        "id": "MAIN_FVT_OMNIA_CLI_V013",
        "title": 'Verify omnia-cli logs --help runs',
    },
    "cli_logs_no_opt_omnia_log": {
        "id": "MAIN_FVT_OMNIA_CLI_V014",
        "title": 'Verify omnia-cli does not search /opt/omnia/log',
    },
    "cli_logs_limit": {
        "id": "MAIN_FVT_OMNIA_CLI_V015",
        "title": 'Verify omnia-cli logs --limit flag works',
    },
    "cli_logs_limit_invalid": {
        "id": "MAIN_FVT_OMNIA_CLI_V016",
        "title": 'Verify omnia-cli logs --limit rejects invalid values',
    },
    "cli_logs_limit_short": {
        "id": "MAIN_FVT_OMNIA_CLI_V017",
        "title": 'Verify omnia-cli logs -l short form works',
    },
    "cli_help_output": {
        "id": "MAIN_FVT_OMNIA_CLI_E001",
        "title": 'Verify omnia-cli help returns usage text',
    },
    "cli_version_output": {
        "id": "MAIN_FVT_OMNIA_CLI_E002",
        "title": 'Verify omnia-cli version shows release info',
    },
    # -- SETUP --
    "base_dirs_created": {
        "id": "MAIN_FVT_SETUP_V005",
        "title": 'Verify base directories created',
    },
    "activate_helper": {
        "id": "MAIN_FVT_SETUP_V006",
        "title": 'Verify activate-omnia.sh helper script created',
    },
    "env_file_installed": {
        "id": "MAIN_FVT_SETUP_V001",
        "title": 'Verify omnia.env installed at /etc/omnia/omnia.env',
    },
    "profile_drop_in": {
        "id": "MAIN_FVT_SETUP_V002",
        "title": 'Verify /etc/profile.d/omnia-env.sh exists',
    },
    "env_vars_loaded": {
        "id": "MAIN_FVT_SETUP_V003",
        "title": 'Verify environment variables are set after install',
    },
    "env_source_validation": {
        "id": "MAIN_FVT_SETUP_V004",
        "title": 'Verify env validation rejects missing SYSTEM_ADMIN_NIC_IPV4',
    },
    "deploy_setup_venv": {
        "id": "MAIN_FVT_SETUP_E001",
        "title": 'Deploy: omnia.sh --setup-venv --deps-only',
    },
    "venv_created": {
        "id": "MAIN_FVT_SETUP_V007",
        "title": 'Verify Python venv created at OMNIA_VENV_PATH',
    },
    "ansible_available": {
        "id": "MAIN_FVT_SETUP_V008",
        "title": 'Verify ansible is available in venv',
    },
    "pip_packages_installed": {
        "id": "MAIN_FVT_SETUP_V009",
        "title": 'Verify all Python requirements installed in venv',
    },
    "galaxy_collections_installed": {
        "id": "MAIN_FVT_SETUP_V010",
        "title": 'Verify installed Galaxy collections and versions',
    },
    # -- NFT --
    "cli_status_performance": {
        "id": "MAIN_NFT_007",
        "title": 'NFT: omnia-cli status performance',
    },
    "cli_help_performance": {
        "id": "MAIN_NFT_011",
        "title": 'NFT: omnia-cli help performance',
    },
    "setup_venv_idempotent": {
        "id": "MAIN_NFT_003",
        "title": 'NFT: setup-venv idempotency',
    },
    "init_idempotent": {
        "id": "MAIN_NFT_004",
        "title": 'NFT: init idempotency',
    },
    "setup_venv_performance": {
        "id": "MAIN_NFT_001",
        "title": 'NFT: setup-venv --deps-only performance',
    },
    "init_performance": {
        "id": "MAIN_NFT_002",
        "title": 'NFT: init performance',
    },
    "check_deps_performance": {
        "id": "MAIN_NFT_005",
        "title": 'NFT: check-deps performance',
    },
    "env_file_permissions": {
        "id": "MAIN_NFT_006",
        "title": 'NFT: env file permissions',
    },
    "omnia_sh_executable": {
        "id": "MAIN_NFT_008",
        "title": 'NFT: omnia.sh executable',
    },
    "omnia_cli_executable": {
        "id": "MAIN_NFT_009",
        "title": 'NFT: omnia-cli executable',
    },
    "domain_init_scripts_executable": {
        "id": "MAIN_NFT_010",
        "title": 'NFT: domain-init.sh permissions',
    },
}
