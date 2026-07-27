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
Omnia.sh - Messages.

This module contains all messages, status strings, and error instructions
for the omnia.sh automation.
"""

from typing import Dict

# =============================================================================
# TEST NAMES (displayed in test output header)
# =============================================================================

# Test names (displayed in test output header)
TEST_NAMES = {
    # Install tests (pre-install)
    "nfs_validation": "Validate NFS configuration",
    "check_omnia_sh": "Verify omnia.sh script exists",
    "omnia_sh_install": "Run omnia.sh --install",
    "internal_nfs_setup": "Setup internal NFS server",
    # Install verification
    "container_running": "Verify omnia_core container is running",
    "container_file": "Verify omnia_core.container file exists",
    "service_running": "Verify omnia_core service is running",
    "metadata_file": "Verify oim_metadata.yml file exists",
    "ssh_to_container": "Verify passwordless SSH: OIM server → omnia_core",
    "ssh_from_container": "Verify passwordless SSH: omnia_core → OIM server",
    # Additional install verification
    "ssh_key_pair": "Verify SSH key pair (oim_rsa) exists",
    "ssh_config_entry": "Verify SSH config entry for omnia_core",
    "authorized_key": "Verify oim_rsa.pub in authorized_keys",
    "container_image": "Verify omnia_core container image exists",
    "omnia_dir": "Verify /omnia/ directory inside container",
    "log_dirs": "Verify log directories in shared path",
    "omnia_version": "Verify omnia.sh --version output",
    # Uninstall tests
    "omnia_sh_uninstall": "Run omnia.sh --uninstall",
    # Cleanup verification
    "cleanup_container_removed": "Verify omnia_core container is removed",
    "cleanup_service_removed": "Verify omnia_core.container file is removed",
    "cleanup_fstab_removed": "Verify fstab entry is removed",
    "cleanup_mount_removed": "Verify /opt/omnia is unmounted",
    # Additional cleanup verification
    "cleanup_ssh_keys_removed": "Verify SSH key pair removed",
    "cleanup_ssh_config_removed": "Verify SSH config entry removed",
    "cleanup_known_hosts_cleaned": "Verify known_hosts entry cleaned",
}

# Test log messages
TEST_LOG_MSGS = {
    # Pre-install messages
    "nfs_config_valid": "NFS configuration valid: {share_option}/{nfs_type}",
    "nfs_config_invalid": "NFS configuration invalid",
    "download_success": "omnia.sh found",
    "download_failed": "omnia.sh not found",
    "install_success": "omnia.sh --install completed",
    "install_failed": "omnia.sh --install FAILED",
    "internal_nfs_success": "Internal NFS server configured",
    "internal_nfs_failed": "Internal NFS server setup FAILED",
    # Install verification messages
    "container_running": "Container is running",
    "container_not_running": "Container is NOT running",
    "file_exists": "File exists",
    "file_not_found": "File NOT found",
    "service_active": "Service is active",
    "service_inactive": "Service is {status}",
    "ssh_success": "Passwordless SSH successful",
    "ssh_failed": "Passwordless SSH FAILED",
    # Additional install verification messages
    "ssh_key_pair_exists": "SSH key pair found",
    "ssh_key_pair_missing": "SSH key pair NOT found",
    "ssh_config_found": "SSH config entry found",
    "ssh_config_missing": "SSH config entry NOT found",
    "authorized_key_found": "Public key in authorized_keys",
    "authorized_key_missing": "Public key NOT in authorized_keys",
    "container_image_found": "Container image found",
    "container_image_missing": "Container image NOT found",
    "omnia_dir_found": "/omnia/ directory exists",
    "omnia_dir_missing": "/omnia/ directory NOT found",
    "log_dirs_found": "Log directories exist",
    "log_dirs_missing": "Log directories NOT found",
    "version_output": "Version output retrieved",
    "version_failed": "Version output FAILED",
    # Uninstall messages
    "uninstall_success": "omnia.sh --uninstall completed",
    "uninstall_failed": "omnia.sh --uninstall FAILED",
    # Cleanup messages
    "cleanup_container_removed": "Container removed successfully",
    "cleanup_container_still_running": "Container is still running",
    "cleanup_service_removed": "Service file removed",
    "cleanup_service_exists": "Service file still exists",
    "cleanup_fstab_removed": "fstab entry removed",
    "cleanup_fstab_exists": "fstab entry still exists",
    "cleanup_mount_removed": "Mount point removed",
    "cleanup_mount_exists": "Still mounted",
    # Additional cleanup messages
    "cleanup_ssh_keys_removed": "SSH key pair removed",
    "cleanup_ssh_keys_exist": "SSH key pair still exists",
    "cleanup_ssh_config_removed": "SSH config entry removed",
    "cleanup_ssh_config_exists": "SSH config entry still exists",
    "cleanup_known_hosts_cleaned": "known_hosts entry cleaned",
    "cleanup_known_hosts_exists": "known_hosts entry still exists",
}

# Skip messages
SKIP_MSGS = {
    "container_running": "omnia_core container is already running - skipping install",
    "container_not_running": "omnia_core container is not running - skipping uninstall",
    "nfs_validation_failed": "NFS configuration validation failed - cannot proceed",
    "install_failed": "Install test failed - skipping verification tests",
    "not_nfs_external": "Not NFS external - check not applicable for this storage type",
}

# Test assert messages
TEST_ASSERT_MSGS = {
    # Pre-install asserts
    "nfs_config_invalid": (
        "NFS configuration invalid.\n"
        "Missing fields: {missing_fields}\n\n"
        "HOW TO FIX:\n"
        "  1. Set config in omnia_test_config.yml: share_option, nfs_type, nfs_server_ip, nfs_share_path, omnia_shared_path\n"
        "  2. Set credentials in omnia_test_credentials.yml: omnia_core_password\n"
        "  Required fields:\n"
        "     - For NFS external: nfs_server_ip, nfs_share_path, omnia_shared_path, omnia_core_password\n"
        "     - For NFS internal: oim_server_ip, nfs_share_path, omnia_core_password\n"
        "     - For Local: omnia_shared_path, omnia_core_password"
    ),
    "download_failed": (
        "omnia.sh not found.\n"
        "Error: {error}\n\n"
        "HOW TO FIX:\n"
        "  1. Verify the repository structure is intact\n"
        "  2. Ensure src/main/omnia.sh exists in the repo"
    ),
    "install_failed": (
        "omnia.sh --install failed.\n"
        "Error: {error}\n\n"
        "HOW TO FIX:\n"
        "  1. Check omnia.sh output for specific errors\n"
        "  2. Verify NFS/storage configuration\n"
        "  3. Check container logs: podman logs omnia_core"
    ),
    "uninstall_failed": (
        "omnia.sh --uninstall failed.\n"
        "Error: {error}\n\n"
        "HOW TO FIX:\n"
        "  1. Check omnia.sh output for specific errors\n"
        "  2. Manually stop container: podman stop omnia_core\n"
        "  3. Manually remove: podman rm omnia_core"
    ),
    # Install verification asserts
    "container_not_running": "Container '{name}' is not running. Status: {status}",
    "file_not_found": "File not found: {path}",
    "service_not_active": "Expected 'active', got '{status}'",
    "ssh_failed": "SSH failed: {error}",
    "config_missing": "oim_server_ip not configured",
    # Cleanup asserts
    "cleanup_failed": "Cleanup verification failed: {error}",
}

# =============================================================================
# FUNCTION MESSAGES (for omnia_sh_func.py)
# =============================================================================

OMNIA_SH_MSGS: Dict[str, str] = {

    # =========================================================================
    # CONFIGURATION VALIDATION
    # =========================================================================
    "config_valid": "Configuration validation passed",
    "config_invalid": "Configuration validation failed",
    "config_error": "Configuration error: {error}",

    # =========================================================================
    # PREREQUISITES
    # =========================================================================
    "prereq_check_start": "Checking prerequisites for omnia.sh...",
    "prereq_check_pass": "All prerequisites met",
    "prereq_check_fail": "Prerequisites check failed",

    "podman_installed": "Podman is installed: {version}",
    "podman_not_installed": "Podman is NOT installed",
    "podman_install_instruction": """
ACTION REQUIRED: Install Podman.
- Run: sudo dnf install -y podman
- Verify: podman --version
""",

    "hostname_valid": "Hostname is valid: {hostname}",
    "hostname_invalid": "Hostname is invalid or not configured with domain",
    "hostname_instruction": """
ACTION REQUIRED: Configure hostname with domain.
- Set hostname: hostnamectl set-hostname <hostname>.<domain>
- Example: hostnamectl set-hostname oim.example.com
""",

    "image_found": "Omnia core image found: {image}:{tag}",
    "image_not_found": "Omnia core image not found locally",
    "image_build_start": "Building omnia_core image...",
    "image_build_success": "Successfully built omnia_core image",
    "image_build_fail": "Failed to build omnia_core image",
    "image_build_instruction": """
ACTION REQUIRED: Build omnia_core image locally.
- Run: ./omnia.sh --build
""",

    # =========================================================================
    # OMNIA.SH EXECUTION
    # =========================================================================
    "omnia_sh_found": "omnia.sh script found at: {path}",
    "omnia_sh_not_found": "omnia.sh script NOT found at: {path}",
    "omnia_sh_not_found_instruction": """
ACTION REQUIRED: omnia.sh script not found.
- Ensure the omnia repository is cloned and the script is at src/main/omnia.sh.
""",

    "install_start": "Starting omnia.sh --install...",
    "install_success": "omnia.sh --install completed successfully",
    "install_fail": "omnia.sh --install failed",
    "install_timeout": "omnia.sh --install timed out after {timeout} seconds",
    "install_instruction": """
ACTION REQUIRED: omnia.sh installation failed.
- Check the output above for errors.
- Verify all prerequisites are met.
- Check if shared path exists and is writable.
- Error: {error}
""",

    "uninstall_start": "Starting omnia.sh --uninstall...",
    "uninstall_success": "omnia.sh --uninstall completed successfully",
    "uninstall_fail": "omnia.sh --uninstall failed",

    # =========================================================================
    # CONTAINER VERIFICATION
    # =========================================================================
    "container_check_start": "Checking omnia_core container status...",
    "container_running": "Container {container_name} is running",
    "container_not_running": "Container {container_name} is NOT running",
    "container_not_found": "Container {container_name} not found",
    "container_instruction": """
ACTION REQUIRED: Container is not running.
- Check container logs: podman logs {container_name}
- Check systemd service: systemctl status {container_name}.service
- Try restarting: systemctl restart {container_name}.service
""",

    "container_wait_start": "Waiting for container to start (timeout: {timeout}s)...",
    "container_wait_success": "Container started successfully",
    "container_wait_timeout": "Container did not start within {timeout} seconds",

    # =========================================================================
    # SSH VERIFICATION
    # =========================================================================
    "ssh_check_start": "Checking SSH connectivity to omnia_core...",
    "ssh_check_pass": "SSH connection to omnia_core successful",
    "ssh_check_fail": "SSH connection to omnia_core failed",
    "ssh_instruction": """
ACTION REQUIRED: SSH connection failed.
- Check if container is running: podman ps | grep omnia_core
- Check SSH port: ss -tlnp | grep {ssh_port}
- Check SSH config: cat ~/.ssh/config | grep omnia_core
- Try manual SSH: ssh -p {ssh_port} root@localhost
""",

    # =========================================================================
    # DIRECTORY VERIFICATION
    # =========================================================================
    "dir_check_start": "Checking required directories...",
    "dir_exists": "Directory exists: {path}",
    "dir_not_exists": "Directory NOT found: {path}",
    "dir_instruction": """
ACTION REQUIRED: Required directory not found.
- Expected path: {path}
- Check if omnia.sh completed successfully.
- Check shared path permissions.
""",

    # =========================================================================
    # CLEANUP
    # =========================================================================
    "cleanup_start": "Starting cleanup...",
    "cleanup_success": "Cleanup completed successfully",
    "cleanup_fail": "Cleanup failed: {error}",
    "cleanup_skip": "Skipping cleanup (cleanup_after_test: false)",

    # =========================================================================
    # TEST RESULTS
    # =========================================================================
    "test_start": "Starting omnia.sh test...",
    "test_pass": "All omnia.sh tests PASSED",
    "test_fail": "omnia.sh tests FAILED: {failed_count} test(s) failed",
    "test_summary": """
Test Summary:
- Total: {total}
- Passed: {passed}
- Failed: {failed}
""",
}
