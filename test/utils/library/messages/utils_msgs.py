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
Utils Domain — Test Log and Assertion Messages.

All log messages and assertion messages are centralized here.
Test files import these dictionaries and use .format() for dynamic content.
"""

from typing import Dict

# =============================================================================
# LOG MESSAGES
# =============================================================================
# Used by TestLogger.passed(), TestLogger.failed(), TestLogger.skipped()

TEST_LOG_MSGS: Dict[str, str] = {
    # --- Playbook execution ---
    "playbook_success": "Playbook completed successfully in {duration}",
    "playbook_failed": "Playbook failed (rc={rc}) in {duration}",
    "playbook_skipped": "Playbook execution skipped: {reason}",

    # --- Connectivity ---
    "connectivity_ok": "Target host is reachable via SSH",
    "connectivity_failed": "Target host is not reachable: {error}",

    # --- Environment variables ---
    "env_var_present": "Environment variable {var} is set: {value}",
    "env_var_missing": "Environment variable {var} is not set",

    # --- File verification ---
    "file_exists": "File exists: {path}",
    "file_missing": "File not found: {path}",
    "file_valid": "File has valid structure: {path}",
    "file_invalid": "File has invalid structure: {path}",

    # --- Directory verification ---
    "dir_exists": "Directory exists: {path}",
    "dir_missing": "Directory not found: {path}",

    # --- Log collector ---
    "bundle_created": "Log bundle created: {path}",
    "bundle_missing": "Log bundle not found in output directory",
    "metadata_valid": "Metadata file has valid JSON structure",
    "metadata_invalid": "Metadata file has invalid structure: {error}",
    "sha256_present": "SHA256 checksum present in metadata",
    "sha256_missing": "SHA256 checksum missing from metadata",
    "functional_groups_valid": "All functional groups are valid",
    "functional_groups_invalid": "Invalid functional group found: {group}",

    # --- PXE boot ---
    "pxe_config_valid": "PXE boot configuration is valid",
    "pxe_config_invalid": "PXE boot configuration is invalid: {error}",
    "inventory_valid": "Inventory file has valid format",
    "inventory_invalid": "Inventory file has invalid format: {error}",
    "phone_home_enabled": "Phone-home verification is enabled",
    "phone_home_disabled": "Phone-home verification is disabled",
    "failed_nodes_created": "Failed nodes report created: {path}",
    "failed_nodes_missing": "Failed nodes report not found",
    "playbook_failed_as_expected": "Playbook failed as expected: {error}",

    # --- Install OS ---
    "iso_config_valid": "ISO configuration is valid",
    "iso_config_invalid": "ISO configuration is invalid: {error}",
    "iso_credentials_valid": "OS install credentials are valid",
    "iso_credentials_invalid": "OS install credentials are invalid: {error}",
    "custom_iso_created": "Custom ISO created: {path}",
    "custom_iso_missing": "Custom ISO not found in output directory",
    "iso_checksum_valid": "ISO checksum matches expected value",
    "iso_checksum_invalid": "ISO checksum mismatch: expected {expected}, got {actual}",
    "kickstart_injected": "Kickstart configuration injected into ISO",
    "kickstart_missing": "Kickstart configuration not found in ISO",

    # --- Hostname/Domain ---
    "hostname_match": "Hostname matches: {hostname}",
    "hostname_mismatch": "Hostname mismatch: expected {expected}, got {actual}",
    "domain_match": "Domain matches: {domain}",
    "domain_mismatch": "Domain mismatch: expected {expected}, got {actual}",

    # --- Admin IP ---
    "admin_ip_assigned": "Admin IP {ip} is assigned to interface {iface}",
    "admin_ip_not_assigned": "Admin IP {ip} is not assigned to any interface",
}

# =============================================================================
# ASSERTION MESSAGES
# =============================================================================
# Used in assert statements — include HOW TO FIX sections

TEST_ASSERT_MSGS: Dict[str, str] = {
    # --- Playbook failures ---
    "playbook_failed": (
        "Playbook {playbook} --tags {tag} failed (rc={rc}, duration={duration})\n"
        "HOW TO FIX:\n"
        "  1. Check playbook output above for errors\n"
        "  2. Verify input files exist at: {input_path}\n"
        "  3. Run manually: cd {workdir} && ansible-playbook {playbook} --tags {tag} -v\n"
    ),

    # --- Connectivity failures ---
    "connectivity_failed": (
        "Cannot connect to target host: {error}\n"
        "HOW TO FIX:\n"
        "  1. Verify oim_server_ip in test_config.yml is correct\n"
        "  2. Check SSH access: ssh {user}@{host}\n"
        "  3. Verify oim_password in test_creds.yml\n"
    ),

    # --- Environment variable failures ---
    "env_var_missing": (
        "Required environment variable {var} is not set on target\n"
        "HOW TO FIX:\n"
        "  1. Run: omnia.sh --setup-venv\n"
        "  2. Verify /etc/omnia/omnia.env exists\n"
        "  3. Source: source /etc/profile.d/omnia-env.sh\n"
    ),

    # --- File failures ---
    "file_missing": (
        "Required file not found: {path}\n"
        "HOW TO FIX:\n"
        "  1. Run domain-init.sh to copy input files\n"
        "  2. Verify dataset is synced: sync_utils_input: true\n"
        "  3. Check file permissions\n"
    ),
    "file_invalid": (
        "File has invalid structure: {path}\n"
        "Error: {error}\n"
        "HOW TO FIX:\n"
        "  1. Validate YAML syntax: python -c \"import yaml; yaml.safe_load(open('{path}'))\"\n"
        "  2. Check file encoding (must be UTF-8)\n"
        "  3. Compare with template in src/utils/input/\n"
    ),

    # --- Log collector failures ---
    "bundle_missing": (
        "Log bundle not created in output directory: {path}\n"
        "HOW TO FIX:\n"
        "  1. Run collect.yml with --tags bundle\n"
        "  2. Check output directory permissions\n"
        "  3. Verify at least one node is reachable\n"
    ),
    "metadata_invalid": (
        "Metadata file has invalid structure\n"
        "Error: {error}\n"
        "HOW TO FIX:\n"
        "  1. Re-run collect.yml to regenerate metadata\n"
        "  2. Check bundle.yml task for errors\n"
    ),
    "functional_groups_invalid": (
        "Invalid functional group in collect_pxe.yml: {group}\n"
        "Valid groups: {valid_groups}\n"
        "HOW TO FIX:\n"
        "  1. Edit collect_pxe.yml and use valid group names\n"
        "  2. See src/utils/input/collect_pxe.yml for examples\n"
    ),

    # --- PXE boot failures ---
    "pxe_config_invalid": (
        "PXE boot configuration is invalid: {error}\n"
        "HOW TO FIX:\n"
        "  1. Check set_pxe_boot_config.yml syntax\n"
        "  2. Verify all required fields are present\n"
        "  3. Compare with template in src/utils/input/\n"
    ),
    "inventory_invalid": (
        "Inventory file has invalid format: {error}\n"
        "HOW TO FIX:\n"
        "  1. Verify INI format: [bmc] section with host entries\n"
        "  2. Each host needs: admin_ip, hostname variables\n"
        "  3. Example: 100.10.0.73 admin_ip=192.168.1.50 hostname=node01\n"
    ),

    # --- Hostname/Domain failures ---
    "hostname_mismatch": (
        "Hostname mismatch: expected '{expected}', got '{actual}'\n"
        "HOW TO FIX:\n"
        "  1. Set hostname: hostnamectl set-hostname {expected}\n"
        "  2. Update /etc/hosts\n"
        "  3. Re-run omnia.sh --setup-venv\n"
    ),
    "domain_mismatch": (
        "Domain mismatch: expected '{expected}', got '{actual}'\n"
        "HOW TO FIX:\n"
        "  1. Update SYSTEM_DOMAIN_NAME in omnia.env\n"
        "  2. Re-run omnia.sh --setup-venv\n"
    ),

    # --- Admin IP failures ---
    "admin_ip_not_assigned": (
        "Admin IP {ip} is not assigned to any network interface\n"
        "HOW TO FIX:\n"
        "  1. Assign IP to interface: ip addr add {ip}/24 dev <interface>\n"
        "  2. Update SYSTEM_ADMIN_NIC_IPV4 in omnia.env\n"
        "  3. Re-run omnia.sh --setup-venv\n"
    ),

    # --- Install OS failures ---
    "install_os_config_invalid": (
        "install_os configuration is invalid: {error}\n"
        "HOW TO FIX:\n"
        "  1. Check install_os_config.yml syntax\n"
        "  2. Verify required fields are present for your tag (credentials/build_iso/deploy/generate_ks)\n"
        "  3. Compare with template in src/utils/input/install_os_config.yml\n"
    ),
    "install_os_credentials_invalid": (
        "install_os credentials are invalid: {error}\n"
        "HOW TO FIX:\n"
        "  1. Check install_os_credentials.yml syntax\n"
        "  2. Verify bmc_username, bmc_password, os_root_password are set\n"
        "  3. If playbook manages vault, plaintext sync is acceptable for automation\n"
    ),
    "install_os_status_invalid": (
        "install_os_status.yml is invalid: {error}\n"
        "HOW TO FIX:\n"
        "  1. Re-run install_os.yml --tags build_iso or --tags deploy\n"
        "  2. Check /opt/omnia/utils/output/<project>/install_os_status.yml\n"
    ),
    "kickstart_missing": (
        "Kickstart file not found where expected\n"
        "HOW TO FIX:\n"
        "  1. Run install_os.yml --tags build_iso or --tags generate_ks\n"
        "  2. Verify NFS mount is present on the build host\n"
    ),
}
