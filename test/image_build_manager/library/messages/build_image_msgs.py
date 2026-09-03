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
Image Build Manager — Test Messages

All test names, log messages, assertion messages, and function messages
for the build_image FVT automation.
"""

# =============================================================================
# TEST NAMES (displayed in test output header)
# =============================================================================

TEST_NAMES = {
    # Deploy
    "deploy_playbook": (
        "Deploy: image_build_manager ({tag})"
    ),
    "deploy_playbook_full": (
        "Deploy: image_build_manager (default: prepare + build)"
    ),

    # Storage backend
    "storage_backend": (
        "Verify S3 storage backend is configured and operational"
    ),
    "minio_container_running": (
        "Verify MinIO container is running"
    ),

    # S3
    "s3cmd_working": "Verify s3cmd is installed and configured",
    "s3_buckets_created": "Verify required S3 buckets exist",
    "s3_bucket_images": (
        "Verify {arch} images are pushed to S3 bucket"
    ),

    # Registry
    "registry_container_running": (
        "Verify registry container is running"
    ),
    "registry_images": (
        "Verify {arch} base and compute images in registry"
    ),

    # Build status
    "build_status_file": (
        "Verify build_status.yml exists and reports success"
    ),

    # Functional groups
    "functional_groups_built": (
        "Verify all configured {arch} functional groups were built"
    ),

    # Image package verification
    "image_packages": (
        "Verify packages installed in {arch} S3 images"
    ),

    # Cleanup verification
    "containers_removed": (
        "Verify MinIO and registry containers removed after cleanup"
    ),
    "services_removed": (
        "Verify MinIO and registry systemd services stopped after cleanup"
    ),
    "firewall_ports_closed": (
        "Verify firewall ports (9000, 9001, 5000) closed after cleanup"
    ),
    "s3_artifacts_removed": (
        "Verify S3 buckets and artifacts removed after cleanup"
    ),
    "s3cfg_removed": (
        "Verify s3cmd configuration removed after cleanup"
    ),
    "credentials_removed": (
        "Verify credentials files removed after cleanup"
    ),
    "build_output_removed": (
        "Verify build_status.yml removed after cleanup"
    ),
    "registry_cleaned": (
        "Verify registry has no images after cleanup"
    ),

    # Prepare verification
    "clone_status": (
        "Verify repository is cloned and synced on target"
    ),
    "s3cmd_configured": (
        "Verify s3cmd is installed and configured"
    ),
    "firewall_ports_open": (
        "Verify service ports (9000, 9001, 5000) are listening"
    ),
    "services_active": (
        "Verify MinIO and registry systemd services are active"
    ),
    "credentials_present": (
        "Verify credentials file is configured on the execution OIM"
    ),
    "registry_reachable": (
        "Verify container registry is reachable"
    ),

    # Validate verification
    "input_config_exists": (
        "Verify image_build_config.yml exists on target"
    ),
}

# =============================================================================
# TEST LOG MESSAGES
# =============================================================================

TEST_LOG_MSGS = {
    # Container messages
    "container_running": "Container {container} is running",
    "container_not_running": (
        "Container {container} is NOT running"
    ),

    # Storage backend
    "storage_backend_minio": (
        "S3 backend: MinIO (local container)"
    ),
    "storage_backend_powerscale": (
        "S3 backend: PowerScale (external)"
    ),
    "storage_backend_skip_minio_check": (
        "S3 backend is PowerScale — skipping MinIO container check"
    ),

    # S3
    "s3cmd_ok": "s3cmd is installed and working",
    "s3cmd_failed": "s3cmd check failed",
    "s3_buckets_ok": (
        "All {count} required S3 buckets present"
    ),
    "s3_buckets_missing": (
        "{count} S3 bucket(s) missing"
    ),
    "s3_images_ok": (
        "All images pushed to S3 for {count} functional groups"
    ),
    "s3_images_missing": (
        "{count} functional group(s) have missing S3 images"
    ),

    # Registry
    "registry_images_ok": (
        "All {arch} images found in registry"
    ),
    "registry_images_missing": (
        "{count} image(s) missing from registry"
    ),

    # Build status
    "build_status_ok": (
        "build_status.yml exists and overall_status is success"
    ),
    "build_status_failed": (
        "build_status.yml check failed"
    ),

    # Functional groups
    "functional_groups_ok": (
        "All {count} configured {arch} functional groups built"
    ),
    "functional_groups_missing": (
        "{count} functional group(s) not found in build output"
    ),

    # Image packages
    "image_packages_ok": (
        "All packages verified in all {arch} images"
    ),
    "image_packages_failed": (
        "{count} image(s) have missing packages"
    ),

    # Prerequisite
    "squashfs_tools_not_installed": (
        "squashfs-tools package is NOT installed. "
        "Required to mount and verify S3 images."
    ),

    # Clone / sync
    "clone_start": (
        "Cloning repo to {host}:{path}"
    ),
    "clone_exists": (
        "Repo already exists at {host}:{path}"
    ),
    "clone_force": (
        "Force clone: removing {path} on {host}"
    ),
    "sync_dataset_start": (
        "Syncing dataset '{dataset}' to {host}:{path}"
    ),
    "sync_dataset_ok": (
        "Dataset synced successfully"
    ),

    # Cleanup extended
    "services_removed_ok": (
        "All systemd services stopped and removed"
    ),
    "services_still_active": (
        "{count} service(s) still active"
    ),
    "firewall_ports_closed_ok": (
        "All firewall ports closed"
    ),
    "firewall_ports_still_open": (
        "{count} port(s) still open"
    ),
    "s3cfg_removed_ok": "s3cmd configuration removed",
    "s3cfg_still_exists": "s3cmd configuration still exists",
    "credentials_removed_ok": "All credentials files removed",
    "credentials_still_exist": "{count} credential file(s) still exist",
    "build_output_removed_ok": "build_status.yml removed",
    "build_output_still_exists": "build_status.yml still exists",
    "registry_cleaned_ok": "Registry cleaned (no images)",
    "registry_still_has_images": (
        "Registry still has {count} image(s)"
    ),

    # Prepare extended
    "clone_ok": "Repository cloned and synced",
    "clone_failed": "Repository clone check failed",
    "s3cmd_configured_ok": "s3cmd installed and configured",
    "s3cmd_not_configured": "s3cmd not fully configured",
    "firewall_ports_open_ok": "All service ports listening",
    "firewall_ports_missing": "{count} port(s) not listening",
    "services_active_ok": "All systemd services active",
    "services_inactive": "{count} service(s) not active",
    "credentials_present_ok": "Credentials file present",
    "credentials_missing": "Credentials file missing",
    "registry_reachable_ok": "Registry is reachable",
    "registry_not_reachable": "Registry is NOT reachable",

    # Validate extended
    "input_config_ok": "image_build_config.yml present",
    "input_config_missing": "image_build_config.yml not found",

    # repo_ssl_verify
    "repo_ssl_verify_ok": (
        "repo_ssl_verify effective value: {value} ({source})"
    ),
    "repo_ssl_verify_missing": (
        "repo_ssl_verify configuration is invalid"
    ),
    "repo_ssl_verify_applied_ok": (
        "repo_ssl_verify is wired into all build templates"
    ),
    "repo_ssl_verify_not_applied": (
        "repo_ssl_verify wiring missing in {count} template(s)"
    ),
    "repo_ssl_verify_applied_blocked": (
        "Template check blocked by invalid repo_ssl_verify configuration"
    ),

    # cleanup_images
    "cleanup_images_s3_ok": (
        "All S3 images deleted after cleanup_images"
    ),
    "cleanup_images_s3_still_exist": (
        "S3 images still present after cleanup_images"
    ),
    "cleanup_images_registry_ok": (
        "All registry images deleted after cleanup_images"
    ),
    "cleanup_images_registry_still_exist": (
        "Registry images still present after cleanup_images"
    ),

    # Build status
    "build_status_not_found": (
        "build_status.yml not found (build tag not run yet)"
    ),

    # Deploy
    "playbook_start": (
        "Running: {playbook} ({tag})"
    ),
    "playbook_success": (
        "Playbook completed (rc=0, duration={duration:.1f}s)"
    ),
    "playbook_failed": (
        "Playbook failed (rc={rc}, duration={duration:.1f}s)"
    ),

    # Precheck
    "connectivity_ok": "Target host is reachable",
    "connectivity_failed": "Target host connectivity check failed",
    "env_vars_ok": "All required OMNIA env vars present",
    "env_vars_missing": "{count} required env var(s) missing",
    "hostname_domain_ok": "Hostname and domain match omnia.env",
    "hostname_domain_mismatch": "Hostname or domain mismatch",
    "admin_ip_ok": "Admin IP assigned to local interface",
    "admin_ip_not_assigned": "Admin IP not assigned to any interface",
    "omnia_setup_ok": "omnia.sh setup completed",
    "omnia_setup_incomplete": "omnia.sh setup incomplete",
}

# =============================================================================
# TEST ASSERT MESSAGES (user-friendly with instructions)
# =============================================================================

_BORDER = "\u2550" * 74

TEST_ASSERT_MSGS = {
    "container_not_running": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 CONTAINER CHECK FAILED: {container}\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Status: {status}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check container: podman ps -a | grep {container}\n"
        "\u2551   2. Check logs: podman logs {container}\n"
        "\u2551   3. Restart: podman restart {container}\n"
        "\u2551   4. Re-run playbook:\n"
        "\u2551      ansible-playbook image_build_manager.yml\n"
        "\u2551      or: run_validation image_build_manager deploy\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "s3_buckets_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 S3 BUCKET CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing buckets:\n"
        "{missing_list}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check s3cmd: s3cmd ls\n"
        "\u2551   2. Check MinIO: podman logs minio-server\n"
        "\u2551   3. Re-run playbook:\n"
        "\u2551      ansible-playbook image_build_manager.yml\n"
        "\u2551      or: run_validation image_build_manager deploy\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "s3_images_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 S3 IMAGES MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Missing images for functional group(s):\n"
        "{missing_list}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check S3: s3cmd ls -Hr s3://boot-images\n"
        "\u2551   2. Check build logs: ls {log_path}\n"
        "\u2551   3. Re-run playbook:\n"
        "\u2551      ansible-playbook image_build_manager.yml\n"
        "\u2551      or: run_validation image_build_manager deploy\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "registry_images_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 REGISTRY IMAGES MISSING\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Registry: {registry_url}\n"
        "\u2551 Missing:\n"
        "{missing_list}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check registry: regctl repo ls {registry_url}\n"
        "\u2551   2. Check build logs: ls {log_path}\n"
        "\u2551   3. Re-run playbook:\n"
        "\u2551      ansible-playbook image_build_manager.yml\n"
        "\u2551      or: run_validation image_build_manager deploy\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "build_status_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 BUILD STATUS CHECK FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check output: cat {status_path}\n"
        "\u2551   2. Check build logs: ls {log_path}\n"
        "\u2551   3. Re-run playbook:\n"
        "\u2551      ansible-playbook image_build_manager.yml\n"
        "\u2551      or: run_validation image_build_manager deploy\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "playbook_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 PLAYBOOK EXECUTION FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 Playbook: {playbook}\n"
        "\u2551 Tag: {tag}\n"
        "\u2551 Exit code: {rc}\n"
        "\u2551 Duration: {duration:.1f}s\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check the playbook output above\n"
        "\u2551   2. Check logs: ls {log_path}\n"
        "\u2551   3. Re-run playbook:\n"
        "\u2551      ansible-playbook image_build_manager.yml\n"
        "\u2551      or: run_validation image_build_manager deploy\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "connectivity_failed": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 TARGET CONNECTIVITY FAILED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Verify oim_server_ip in test_config.yml\n"
        # gitleaks:allow — user-facing instruction, not a leaked secret
        "\u2551   2. Verify SSH user/password: "
        "./setup_env.sh --set-creds\n"
        "\u2551   3. Test manually: ssh root@<oim_server_ip>\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "env_vars_missing": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 OMNIA ENV VARS MISSING ON TARGET\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: omnia.sh --setup-venv on the target server\n"
        "\u2551   2. Verify: cat /etc/profile.d/omnia-env.sh\n"
        "\u2551   3. Check all required env vars in omnia.env\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "hostname_domain_mismatch": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 HOSTNAME / DOMAIN MISMATCH\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check actual: hostname -s (short), hostname -d (domain)\n"
        "\u2551   2. Update SYSTEM_HOSTNAME / SYSTEM_DOMAIN_NAME in omnia.env\n"
        "\u2551   3. Or: hostnamectl set-hostname <hostname>.<domain>\n"
        "\u2551   4. Re-run: omnia.sh --setup-venv\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "admin_ip_not_assigned": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 ADMIN IP NOT ASSIGNED\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Check assigned IPs: hostname -I\n"
        "\u2551   2. Verify SYSTEM_ADMIN_NIC_IPV4 in omnia.env matches one of them\n"
        "\u2551   3. Re-run: omnia.sh --setup-venv\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),

    "omnia_setup_incomplete": (
        "\n\u2554" + _BORDER + "\u2557\n"
        "\u2551 OMNIA SETUP INCOMPLETE\n"
        "\u2560" + _BORDER + "\u2563\n"
        "\u2551 {error}\n"
        "\u2551\n"
        "\u2551 HOW TO FIX:\n"
        "\u2551   1. Run: ./omnia.sh --setup-venv\n"
        "\u2551   2. Verify: /etc/omnia/omnia.env exists\n"
        "\u2551   3. Verify: /etc/profile.d/omnia-env.sh exists\n"
        "\u255a" + _BORDER + "\u255d\n"
    ),
}

# =============================================================================
# FUNCTION MESSAGES (for library functions)
# =============================================================================

BUILD_IMAGE_MSGS = {
    "validation_summary": (
        "\nValidation Summary:\n"
        "- Total: {total}\n"
        "- Passed: {passed}\n"
        "- Failed: {failed}\n"
        "- Skipped: {skipped}\n"
    ),
}
