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
Repo Manager — Test Case Registry.

Central registry mapping every test to its TC ID and title.
Test files reference ``TEST_CASES["key"]`` to get a consistent
test-case identifier and display name.

Usage in test files::

    from library.vars import TEST_CASES as TC

    tc = TC["deploy_precheck"]
    tl = TestLogger(tc["title"], tc["id"])
"""

TEST_CASES = {
    # ── Deploy (one per scenario) ─────────────────────────────────────────
    "deploy_precheck": {
        "id": "RM_FVT_PRECHECK_E001",
        "title": "Deploy repo_manager (precheck)",
    },
    "deploy_prepare": {
        "id": "RM_FVT_PREPARE_E001",
        "title": "Deploy repo_manager (prepare)",
    },
    "deploy_execute": {
        "id": "RM_FVT_EXECUTE_E001",
        "title": "Deploy repo_manager (execute)",
    },
    "deploy_status": {
        "id": "RM_FVT_STATUS_E001",
        "title": "Deploy repo_manager (status)",
    },
    "deploy_cleanup": {
        "id": "RM_FVT_CLEANUP_E001",
        "title": "Deploy repo_manager (cleanup)",
    },
    "deploy_cleanup_repos": {
        "id": "RM_FVT_CLEANUP_REPOS_E001",
        "title": "Deploy repo_manager (cleanup_repos)",
    },
    "deploy_credentials": {
        "id": "RM_FVT_CREDENTIALS_E001",
        "title": "Deploy repo_manager (credentials)",
    },
    # ── Catalog deploy (one per operation) ────────────────────────────────
    "deploy_catalog_generate": {
        "id": "RM_FVT_CATALOG_GENERATE_E001",
        "title": "Deploy repo_manager (catalog_generate)",
    },
    "deploy_catalog_add": {
        "id": "RM_FVT_CATALOG_ADD_E001",
        "title": "Deploy repo_manager (catalog_add)",
    },
    "deploy_catalog_delete": {
        "id": "RM_FVT_CATALOG_DELETE_E001",
        "title": "Deploy repo_manager (catalog_delete)",
    },
    "deploy_catalog_validate": {
        "id": "RM_FVT_CATALOG_VALIDATE_E001",
        "title": "Deploy repo_manager (catalog_validate)",
    },
    # ── User Registry deploy ──────────────────────────────────────────────
    "deploy_user_registry": {
        "id": "RM_FVT_USER_REGISTRY_E001",
        "title": "Deploy repo_manager (user_registry validation)",
    },
    # ── Precheck verification ─────────────────────────────────────────────
    "input_config_exists": {
        "id": "RM_FVT_PRECHECK_V001",
        "title": "Verify repo_manager_config.yml exists",
    },
    "endpoint_config_exists": {
        "id": "RM_FVT_PRECHECK_V002",
        "title": "Verify repo_manager_endpoint_config.yml exists",
    },
    "credentials_present": {
        "id": "RM_FVT_PRECHECK_V003",
        "title": "Verify credentials file is present",
    },
    "precheck_no_credentials": {
        "id": "RM_FVT_PRECHECK_V004",
        "title": "Verify precheck completes without credential prompting",
    },
    # ── Prepare verification ──────────────────────────────────────────────
    "pulp_container_running": {
        "id": "RM_FVT_PREPARE_V001",
        "title": "Verify Pulp container is running",
    },
    "pulp_status_healthy": {
        "id": "RM_FVT_PREPARE_V002",
        "title": "Verify Pulp status is healthy",
    },
    "pulp_endpoint_reachable": {
        "id": "RM_FVT_PREPARE_V003",
        "title": "Verify Pulp endpoint reachable",
    },
    "pulp_cli_configured": {
        "id": "RM_FVT_PREPARE_V004",
        "title": "Verify Pulp CLI configured",
    },
    "pulp_certificates_exist": {
        "id": "RM_FVT_PREPARE_V005",
        "title": "Verify Pulp SSL certificates exist",
    },
    "pulp_cli_repository_list": {
        "id": "RM_FVT_PREPARE_V006",
        "title": "Verify Pulp CLI can list RPM repositories",
    },
    "pulp_api_detailed_status": {
        "id": "RM_FVT_PREPARE_V007",
        "title": "Verify Pulp API detailed health (DB, workers, content apps, storage)",
    },
    "collect_credentials": {
        "id": "RM_FVT_PREPARE_E002",
        "title": "Verify collect_repo_credentials role functionality",
    },
    "credential_encryption": {
        "id": "RM_FVT_PREPARE_E003",
        "title": "Verify credential encryption and vault handling",
    },
    # ── Execute verification ──────────────────────────────────────────────
    "repo_status_exists": {
        "id": "RM_FVT_EXECUTE_V001",
        "title": "Verify repo_status.yml generated",
    },
    "repo_status_success": {
        "id": "RM_FVT_EXECUTE_V002",
        "title": "Verify overall_status is success",
    },
    "slurm_custom_repo_present": {
        "id": "RM_FVT_EXECUTE_V003",
        "title": "Verify slurm_custom repo present",
    },
    "epel_repo_present": {
        "id": "RM_FVT_EXECUTE_V004",
        "title": "Verify epel repo present",
    },
    "x86_64_repos_present": {
        "id": "RM_FVT_EXECUTE_V005",
        "title": "Verify x86_64 repositories present",
    },
    "file_repos_present": {
        "id": "RM_FVT_EXECUTE_V006",
        "title": "Verify file repositories present",
    },
    "software_download_status": {
        "id": "RM_FVT_EXECUTE_V007",
        "title": "Verify software.csv download status per architecture",
    },
    "per_software_package_status": {
        "id": "RM_FVT_EXECUTE_V008",
        "title": "Verify per-software status.csv for individual package results",
    },
    "pulp_repositories_synced": {
        "id": "RM_FVT_EXECUTE_V009",
        "title": "Verify all RPM repositories have sync indicator",
    },
    "pulp_distributions_published": {
        "id": "RM_FVT_EXECUTE_V010",
        "title": "Verify all RPM distributions are published",
    },
    "container_repos_synced": {
        "id": "RM_FVT_EXECUTE_V011",
        "title": "Verify all container image repositories are synced",
    },
    "file_repos_synced": {
        "id": "RM_FVT_EXECUTE_V012",
        "title": "Verify all file repositories are synced",
    },
    "pulp_content_accessible": {
        "id": "RM_FVT_EXECUTE_V013",
        "title": "Verify RPM content is reachable via HTTPS",
    },
    "software_packages_in_pulp": {
        "id": "RM_FVT_EXECUTE_V014",
        "title": "Verify all RPM packages from software_config.json are in Pulp",
    },
    # ── Status verification ───────────────────────────────────────────────
    "repo_status_regenerated": {
        "id": "RM_FVT_STATUS_V001",
        "title": "Verify repo_status.yml regenerated",
    },
    "repo_status_success_after_status": {
        "id": "RM_FVT_STATUS_V002",
        "title": "Verify overall_status is success after regeneration",
    },
    # ── Cleanup verification ──────────────────────────────────────────────
    "pulp_container_removed": {
        "id": "RM_FVT_CLEANUP_V001",
        "title": "Verify Pulp container removed",
    },
    "pulp_cli_preserved": {
        "id": "RM_FVT_CLEANUP_V002",
        "title": "Verify managed Pulp CLI preserved",
    },
    "pulp_directories_removed": {
        "id": "RM_FVT_CLEANUP_V003",
        "title": "Verify Pulp directories removed",
    },
    # ── Selective cleanup verification ────────────────────────────────────
    "exact_repository_cleanup": {
        "id": "RM_FVT_CLEANUP_REPOS_E001",
        "title": "Deploy exact repository cleanup",
    },
    "exact_repository_absent": {
        "id": "RM_FVT_CLEANUP_REPOS_V001",
        "title": "Verify target repository is absent while Pulp is healthy",
    },
    "cleanup_invalidates_repo_status": {
        "id": "RM_FVT_CLEANUP_REPOS_V002",
        "title": "Verify stale consumer URLs removed after cleanup",
    },
    "cleanup_status_records_success": {
        "id": "RM_FVT_CLEANUP_REPOS_V003",
        "title": "Verify cleanup CSV records the requested identity",
    },
    # ── Policy verification ───────────────────────────────────────────────
    "per_repo_policy_override": {
        "id": "RM_FVT_POLICY_V001",
        "title": "Per-repo policy overrides global repo_config",
    },
    "per_repo_caching_override": {
        "id": "RM_FVT_POLICY_V002",
        "title": "Per-repo caching overrides global caching_policy",
    },
    "per_repo_complete_override": {
        "id": "RM_FVT_POLICY_V003",
        "title": "Per-repo completely overrides global settings",
    },
    "per_repo_policy_only": {
        "id": "RM_FVT_POLICY_V004",
        "title": "Per-repo policy only, caching from global",
    },
    "per_repo_caching_only": {
        "id": "RM_FVT_POLICY_V005",
        "title": "Per-repo caching only, policy from global",
    },
    "empty_per_repo_config": {
        "id": "RM_FVT_POLICY_V006",
        "title": "Empty per-repo config uses global settings",
    },
    "policy_always_caching_false": {
        "id": "RM_FVT_POLICY_V007",
        "title": "policy: always + caching: false = immediate",
    },
    "policy_always_caching_true": {
        "id": "RM_FVT_POLICY_V008",
        "title": "policy: always + caching: true = on_demand",
    },
    "policy_partial_caching_false": {
        "id": "RM_FVT_POLICY_V009",
        "title": "policy: partial + caching: false = streamed",
    },
    "policy_partial_caching_true": {
        "id": "RM_FVT_POLICY_V010",
        "title": "policy: partial + caching: true = on_demand",
    },
    "subscription_repo_per_repo_override": {
        "id": "RM_FVT_POLICY_V011",
        "title": "Subscription repo with per-repo override",
    },
    "url_repo_per_repo_override": {
        "id": "RM_FVT_POLICY_V012",
        "title": "URL repo with per-repo override",
    },
    "subscription_and_url_identical_behavior": {
        "id": "RM_FVT_POLICY_V013",
        "title": "Subscription and URL repos behave identically",
    },
    "pulp_mode_in_repo_status": {
        "id": "RM_FVT_POLICY_V014",
        "title": "repo_status.yml reflects correct Pulp mode",
    },
    "actual_pulp_repository_policy": {
        "id": "RM_FVT_POLICY_V015",
        "title": "Actual Pulp repository has correct policy",
    },
    "disk_space_savings": {
        "id": "RM_FVT_POLICY_V016",
        "title": "On-demand repos save disk space",
    },
    "pulp_remote_policy_matches_config": {
        "id": "RM_FVT_POLICY_V017",
        "title": "Pulp remote policy matches resolved configuration",
    },
    "pulp_remote_policy_immediate_mode": {
        "id": "RM_FVT_POLICY_V018",
        "title": "Pulp remote has immediate policy for always+false",
    },
    "pulp_remote_policy_on_demand_mode": {
        "id": "RM_FVT_POLICY_V019",
        "title": "Pulp remote has on_demand policy for partial+true",
    },
    "multiple_repos_policy_resolution": {
        "id": "RM_FVT_POLICY_V020",
        "title": "Multiple repos have correct Pulp policies",
    },
    "pulp_repository_exists": {
        "id": "RM_FVT_POLICY_V021",
        "title": "Pulp repositories exist for configured repos",
    },
    # ── User Registry verification ────────────────────────────────────────
    "user_registry_section_exists": {
        "id": "RM_FVT_USER_REGISTRY_V001",
        "title": "Verify registries section exists in config",
    },
    "user_registry_structure_valid": {
        "id": "RM_FVT_USER_REGISTRY_V002",
        "title": "Verify registry entries have valid structure",
    },
    "user_registry_base_url_valid": {
        "id": "RM_FVT_USER_REGISTRY_V003",
        "title": "Verify registry base_url is a valid HTTP(S) origin",
    },
    "user_registry_reachable": {
        "id": "RM_FVT_USER_REGISTRY_V004",
        "title": "Verify configured registries are reachable",
    },
    "user_registry_tls_cert_paths_valid": {
        "id": "RM_FVT_USER_REGISTRY_V005",
        "title": "Verify TLS certificate paths are valid",
    },
    "user_registry_tls_pair_consistent": {
        "id": "RM_FVT_USER_REGISTRY_V006",
        "title": "Verify client cert and key configured together",
    },
    "user_registry_auth_type_valid": {
        "id": "RM_FVT_USER_REGISTRY_V007",
        "title": "Verify registry auth type is valid",
    },
    "user_registry_credentials_present": {
        "id": "RM_FVT_USER_REGISTRY_V008",
        "title": "Verify registry credentials are configured",
    },
    # ── User Registry negative ────────────────────────────────────────────
    "user_registry_neg_missing_config": {
        "id": "RM_FVT_USER_REGISTRY_NEG_001",
        "title": "Validation fails with missing config file",
    },
    "user_registry_neg_invalid_base_url": {
        "id": "RM_FVT_USER_REGISTRY_NEG_002",
        "title": "Detects invalid base_url",
    },
    "user_registry_neg_incomplete_tls_pair": {
        "id": "RM_FVT_USER_REGISTRY_NEG_003",
        "title": "Detects incomplete TLS cert/key pair",
    },
    "user_registry_neg_unsupported_auth_type": {
        "id": "RM_FVT_USER_REGISTRY_NEG_004",
        "title": "Detects unsupported auth type",
    },
    "user_registry_neg_missing_cert_paths": {
        "id": "RM_FVT_USER_REGISTRY_NEG_005",
        "title": "Detects missing cert paths on disk",
    },
    "user_registry_neg_missing_vault_path": {
        "id": "RM_FVT_USER_REGISTRY_NEG_006",
        "title": "Detects missing vault_path for basic auth",
    },
    # ── Negative error scenarios ──────────────────────────────────────────
    "neg_missing_credentials": {
        "id": "RM_FVT_NEG_001",
        "title": "Deploy fails with missing credentials",
    },
    "neg_invalid_endpoint_config": {
        "id": "RM_FVT_NEG_002",
        "title": "Deploy fails with invalid endpoint config",
    },
    "neg_invalid_repo_url": {
        "id": "RM_FVT_NEG_003",
        "title": "Download fails with invalid repository URL",
    },
    "neg_missing_repo_status": {
        "id": "RM_FVT_NEG_004",
        "title": "Status check fails with missing repo_status.yml",
    },
    "neg_pulp_not_running": {
        "id": "RM_FVT_NEG_005",
        "title": "Cleanup fails when Pulp container not running",
    },
    "neg_invalid_auth": {
        "id": "RM_FVT_NEG_006",
        "title": "Pulp CLI fails with invalid authentication",
    },
    # ── Catalog verification ──────────────────────────────────────────────
    "catalog_input_dir_exists": {
        "id": "RM_FVT_CATALOG_GENERATE_V001",
        "title": "Verify catalog input directory exists",
    },
    "catalog_file_exists": {
        "id": "RM_FVT_CATALOG_GENERATE_V002",
        "title": "Verify catalog file exists after generate",
    },
    "catalog_structure_valid": {
        "id": "RM_FVT_CATALOG_GENERATE_V003",
        "title": "Verify catalog structure is valid",
    },
    "catalog_functional_layers": {
        "id": "RM_FVT_CATALOG_GENERATE_V004",
        "title": "Verify catalog has functional layers",
    },
    "catalog_groups": {
        "id": "RM_FVT_CATALOG_GENERATE_V005",
        "title": "Verify catalog has groups",
    },
    "catalog_packages": {
        "id": "RM_FVT_CATALOG_GENERATE_V006",
        "title": "Verify catalog has packages",
    },
    "catalog_log_file_exists": {
        "id": "RM_FVT_CATALOG_GENERATE_V007",
        "title": "Verify catalog log file exists",
    },
    "catalog_add_completed": {
        "id": "RM_FVT_CATALOG_ADD_V001",
        "title": "Verify catalog add operation completed",
    },
    "catalog_delete_completed": {
        "id": "RM_FVT_CATALOG_DELETE_V001",
        "title": "Verify catalog delete operation completed",
    },
    "catalog_validate_completed": {
        "id": "RM_FVT_CATALOG_VALIDATE_V001",
        "title": "Verify catalog validation completed",
    },
    "catalog_validate_log_exists": {
        "id": "RM_FVT_CATALOG_VALIDATE_V002",
        "title": "Verify catalog validation log file exists",
    },
    # ── Catalog negative ──────────────────────────────────────────────────
    "catalog_neg_generate_missing_input": {
        "id": "RM_FVT_CATALOG_NEG_001",
        "title": "Verify catalog_generate fails with missing input file",
    },
    "catalog_neg_add_missing_input": {
        "id": "RM_FVT_CATALOG_NEG_002",
        "title": "Verify catalog_add fails with missing input file",
    },
    "catalog_neg_delete_missing_input": {
        "id": "RM_FVT_CATALOG_NEG_003",
        "title": "Verify catalog_delete fails with missing input file",
    },
    "catalog_neg_input_dir_validation": {
        "id": "RM_FVT_CATALOG_NEG_004",
        "title": "Verify catalog input directory validation",
    },
    "catalog_neg_structure_validation": {
        "id": "RM_FVT_CATALOG_NEG_005",
        "title": "Verify catalog structure validation",
    },
    "catalog_neg_file_existence": {
        "id": "RM_FVT_CATALOG_NEG_006",
        "title": "Verify catalog file existence validation",
    },
    "catalog_neg_log_validation": {
        "id": "RM_FVT_CATALOG_NEG_007",
        "title": "Verify catalog log file validation",
    },
}
