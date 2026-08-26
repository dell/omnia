# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Repo Manager — Test names and assertion/log messages.
"""

TEST_NAMES = {
    # Precheck
    "input_config_exists": "Precheck repo_manager_config.yml exists",
    "endpoint_config_exists": "Precheck repo_manager_endpoint_config.yml exists",
    "credentials_present": "Precheck credentials file present",
    # Prepare
    "pulp_container_running": "Verify Pulp container is running",
    "pulp_status_healthy": "Verify Pulp status is healthy",
    "pulp_endpoint_reachable": "Verify Pulp endpoint reachable",
    "pulp_cli_configured": "Verify Pulp CLI configured",
    "pulp_certificates_exist": "Verify Pulp SSL certificates exist",
    "pulp_cli_repository_list": "Verify Pulp CLI can list RPM repositories",
    "pulp_api_detailed_status": (
        "Verify Pulp API detailed health (DB, workers, content apps, storage)"
    ),
    # Execute
    "repo_status_exists": "Verify repo_status.yml generated",
    "repo_status_success": "Verify overall_status is success",
    "slurm_custom_repo_present": "Verify slurm_custom repo present",
    "epel_repo_present": "Verify epel repo present",
    "x86_64_repos_present": "Verify x86_64 repositories present",
    "file_repos_present": "Verify file repositories present",
    "software_download_status": "Verify software.csv download status per architecture",
    "per_software_package_status": (
        "Verify per-software status.csv for individual package download results"
    ),
    "pulp_repositories_synced": (
        "Verify all RPM repositories have latest_version_href (sync indicator)"
    ),
    "pulp_distributions_published": (
        "Verify all RPM distributions are published with repository attachment"
    ),
    "container_repos_synced": "Verify all container image repositories are synced",
    "file_repos_synced": "Verify all file repositories (tarball, git, etc.) are synced",
    "pulp_content_accessible": "Verify RPM content is reachable via HTTPS (repomd.xml check)",
    "software_packages_in_pulp": (
        "Verify all RPM packages from software_config.json are present in Pulp"
    ),
    # Status
    "repo_status_regenerated": "Verify repo_status.yml regenerated",
    # Cleanup
    "pulp_container_removed": "Verify Pulp container removed",
    "pulp_cli_removed": "Verify Pulp CLI removed",
    "pulp_directories_removed": "Verify Pulp directories removed",
}

TEST_LOG_MSGS = {
    # Precheck
    "input_config_ok": "repo_manager_config.yml found",
    "input_config_missing": "repo_manager_config.yml is missing",
    "endpoint_config_ok": "repo_manager_endpoint_config.yml found",
    "endpoint_config_missing": "repo_manager_endpoint_config.yml is missing",
    "credentials_ok": "Credentials file found",
    "credentials_missing": "Credentials file is missing",
    # Prepare
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
    "pulp_cli_repo_list_ok": "Pulp CLI can list RPM repositories",
    "pulp_cli_repo_list_fail": "Pulp CLI repository list command failed",
    "pulp_api_detailed_ok": "Pulp API all components healthy",
    "pulp_api_detailed_fail": "Pulp API health check failed for some components",
    # Execute
    "repo_status_exists": "repo_status.yml exists",
    "repo_status_missing": "repo_status.yml missing",
    "repo_status_success": "overall_status is success",
    "repo_status_failed": "overall_status is not success",
    "repo_present": "Repository {repo} found",
    "repo_missing": "Repository {repo} not found",
    "file_repo_present": "File repo {repo} found",
    "file_repo_missing": "File repo {repo} not found",
    "software_download_ok": "All software downloads successful",
    "software_download_failed": "Software download status shows failures",
    "per_software_pkg_ok": "All per-software packages successful",
    "per_software_pkg_failed": "Per-software package status shows failures",
    "pulp_repos_synced": "All RPM repositories synced",
    "pulp_repos_not_synced": "Some RPM repositories not synced",
    "pulp_distributions_ok": "All RPM distributions published",
    "pulp_distributions_missing": "Some RPM distributions not published",
    "container_repos_synced": "All container repositories synced",
    "container_repos_not_synced": "Some container repositories not synced",
    "file_repos_synced": "All file repositories synced",
    "file_repos_not_synced": "Some file repositories not synced",
    "pulp_content_accessible": "All RPM distributions accessible via HTTPS",
    "pulp_content_not_accessible": "Some RPM distributions not accessible via HTTPS",
    "software_packages_ok": "All software packages found in Pulp",
    "software_packages_missing": "Some software packages missing from Pulp",
    "software_config_error": "Software configuration file error",
    # Cleanup
    "pulp_container_removed": "Pulp container removed",
    "pulp_container_still_exists": "Pulp container still exists",
    "pulp_cli_removed": "Pulp CLI symlink removed",
    "pulp_cli_still_exists": "Pulp CLI symlink still exists",
    "pulp_dirs_removed": "Pulp directories removed",
    "pulp_dirs_still_exist": "Pulp directories still exist",
}

TEST_ASSERT_MSGS = {
    "input_config_missing": "repo_manager_config.yml is required for precheck",
    "endpoint_config_missing": "repo_manager_endpoint_config.yml is required",
    "credentials_missing": "Credentials file is required for Pulp deployment",
    "pulp_container_not_running": "Pulp container must be running after prepare",
    "pulp_status_failed": "Pulp status command must succeed",
    "pulp_endpoint_not_reachable": "Pulp endpoint must be reachable",
    "pulp_cli_not_configured": "Pulp CLI must be configured",
    "pulp_certs_missing": "Pulp SSL certificates must exist for HTTPS",
    "pulp_cli_repo_list_failed": "Pulp CLI repository list command must succeed",
    "pulp_api_detailed_unhealthy": "Pulp API health check must pass for all components",
    "repo_status_missing": "repo_status.yml must be generated",
    "repo_status_not_success": "repo_status.yml must report overall_status = success",
    "repo_not_found": "Repository not found in repo_status.yml",
    "software_download_failed": "Software download status must show all successful",
    "per_software_pkg_failed": "Per-software package status must show all successful",
    "pulp_repos_not_synced": "All RPM repositories must be synced",
    "pulp_distributions_missing": "All RPM distributions must be published",
    "container_repos_not_synced": "All container repositories must be synced",
    "file_repos_not_synced": "All file repositories must be synced",
    "pulp_content_not_accessible": "All RPM distributions must be accessible via HTTPS",
    "software_packages_missing": "All software packages must be present in Pulp",
    "software_config_error": "Software configuration file must be valid and present",
    "pulp_container_still_exists": "Pulp container must be removed after cleanup",
    "pulp_cli_still_exists": "Pulp CLI symlink must be removed after cleanup",
    "pulp_dirs_still_exist": "Pulp directories must be removed after cleanup",
}
