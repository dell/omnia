# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Test names and assertion/log messages.
"""

TEST_NAMES = {
    # Validate
    "input_config_exists": "Validate repo_manager_config.yml exists",
    "endpoint_config_exists": "Validate repo_manager_endpoint_config.yml exists",
    "credentials_present": "Validate credentials file present",
    # Deploy
    "pulp_container_running": "Verify Pulp container is running",
    "pulp_status_healthy": "Verify Pulp status is healthy",
    "pulp_endpoint_reachable": "Verify Pulp endpoint reachable",
    "pulp_cli_configured": "Verify Pulp CLI configured",
    "pulp_certificates_exist": "Verify Pulp SSL certificates exist",
    # Download
    "repo_status_exists": "Verify repo_status.yml generated",
    "repo_status_success": "Verify overall_status is success",
    "slurm_custom_repo_present": "Verify slurm_custom repo present",
    "epel_repo_present": "Verify epel repo present",
    "x86_64_repos_present": "Verify x86_64 repositories present",
    "file_repos_present": "Verify file repositories present",
    # Status
    "repo_status_regenerated": "Verify repo_status.yml regenerated",
    # Cleanup
    "pulp_container_removed": "Verify Pulp container removed",
    "pulp_cli_removed": "Verify Pulp CLI removed",
    "pulp_directories_removed": "Verify Pulp directories removed",
}

TEST_LOG_MSGS = {
    # Validate
    "input_config_ok": "repo_manager_config.yml found",
    "input_config_missing": "repo_manager_config.yml is missing",
    "endpoint_config_ok": "repo_manager_endpoint_config.yml found",
    "endpoint_config_missing": "repo_manager_endpoint_config.yml is missing",
    "credentials_ok": "Credentials file found",
    "credentials_missing": "Credentials file is missing",
    # Deploy
    "pulp_container_running": "Pulp container is running",
    "pulp_container_not_running": "Pulp container is not running",
    "pulp_status_ok": "Pulp status command succeeded",
    "pulp_status_failed": "Pulp status command failed",
    "pulp_endpoint_ok": "Pulp endpoint reachable",
    "pulp_endpoint_failed": "Pulp endpoint not reachable",
    "pulp_cli_ok": "Pulp CLI configured",
    "pulp_cli_failed": "Pulp CLI not configured",
    "pulp_certs_ok": "Pulp SSL certificates exist",
    "pulp_certs_missing": "Pulp SSL certificates missing",
    # Download
    "repo_status_exists": "repo_status.yml exists",
    "repo_status_missing": "repo_status.yml missing",
    "repo_status_success": "overall_status is success",
    "repo_status_failed": "overall_status is not success",
    "repo_present": "Repository {repo} found",
    "repo_missing": "Repository {repo} not found",
    "file_repo_present": "File repo {repo} found",
    "file_repo_missing": "File repo {repo} not found",
    # Cleanup
    "pulp_container_removed": "Pulp container removed",
    "pulp_container_still_exists": "Pulp container still exists",
    "pulp_cli_removed": "Pulp CLI symlink removed",
    "pulp_cli_still_exists": "Pulp CLI symlink still exists",
    "pulp_dirs_removed": "Pulp directories removed",
    "pulp_dirs_still_exist": "Pulp directories still exist",
}

TEST_ASSERT_MSGS = {
    "input_config_missing": "repo_manager_config.yml is required for validation",
    "endpoint_config_missing": "repo_manager_endpoint_config.yml is required",
    "credentials_missing": "Credentials file is required for Pulp deployment",
    "pulp_container_not_running": "Pulp container must be running after deploy",
    "pulp_status_failed": "Pulp status command must succeed",
    "pulp_endpoint_not_reachable": "Pulp endpoint must be reachable",
    "pulp_cli_not_configured": "Pulp CLI must be configured",
    "pulp_certs_missing": "Pulp SSL certificates must exist for HTTPS",
    "repo_status_missing": "repo_status.yml must be generated",
    "repo_status_not_success": "repo_status.yml must report overall_status = success",
    "repo_not_found": "Repository not found in repo_status.yml",
    "pulp_container_still_exists": "Pulp container must be removed after cleanup",
    "pulp_cli_still_exists": "Pulp CLI symlink must be removed after cleanup",
    "pulp_dirs_still_exist": "Pulp directories must be removed after cleanup",
}
