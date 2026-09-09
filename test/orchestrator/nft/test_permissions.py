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
Orchestrator — Non-Functional Security and Permission Tests.

Verifies that sensitive files have correct permissions and encryption:
  - Credential files have restricted permissions
  - SSH keys have proper permissions
  - Log files don't expose sensitive information
  - Ansible vault encryption is properly configured

Test cases:
    NFT_OR_008: Credential file permissions (0640 or stricter)
    NFT_OR_009: SSH key permissions (0600)
    NFT_OR_010: Sensitive log file permissions
    NFT_OR_011: Ansible vault encryption verification
"""

import pytest

from library.functions import TestLogger, load_test_config, run_on_host
from library.vars.common_vars import (
    CREDENTIALS_FILE_NAME,
    CREDENTIALS_KEY_NAME,
    INPUT_PATH_TEMPLATE,
)


def _get_input_path() -> str:
    """Return the orchestrator input path for the configured project."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    return INPUT_PATH_TEMPLATE.format(project=project)


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(1)
def test_credential_file_permissions(host):
    """NFT_OR_008: Verify credential files have restricted permissions (0640 or stricter).

    Checks that omnia_config_credentials.yml has permissions that prevent
    world-readable access (should be 0640 or stricter like 0600).
    """
    tl = TestLogger("NFT: Credential file permissions", "NFT_OR_008")

    input_path = _get_input_path()
    cred_path = f"{input_path}/{CREDENTIALS_FILE_NAME}"

    result = run_on_host(
        host,
        f"stat -c '%a' {cred_path} 2>/dev/null",
    )

    if result.rc != 0:
        tl.skipped(f"Credential file not found: {cred_path}")
        pytest.skip(f"Credential file not found: {cred_path}")

    perms = result.stdout.strip()
    # Check if permissions are 0640 or stricter (no world read)
    # 0640 = rw-r----- (owner read/write, group read, no world permissions)
    # 0600 = rw------- (owner only)
    is_restricted = (
        perms in ["640", "600"] or
        (len(perms) == 3 and perms[2] == "0")  # No world permissions
    )

    if is_restricted:
        tl.passed(
            f"Credential file has restricted permissions ({perms})",
            f"File: {cred_path}\nPermissions: {perms}",
        )
    else:
        tl.failed(
            f"Credential file has overly permissive permissions ({perms})",
            f"File: {cred_path}\nCurrent permissions: {perms}\n"
            f"Expected: 0640 or stricter (no world read)",
        )

    assert is_restricted, (
        f"Credential file {cred_path} has permissions {perms}, "
        f"expected 0640 or stricter"
    )


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(2)
def test_ssh_key_permissions(host):
    """NFT_OR_009: Verify SSH keys have proper permissions (0600).

    Checks that SSH private keys in the orchestrator input directory
    have permissions that prevent unauthorized access (should be 0600).
    """
    tl = TestLogger("NFT: SSH key permissions", "NFT_OR_009")

    input_path = _get_input_path()

    # Check for common SSH key files
    ssh_key_patterns = [
        "id_rsa",
        "id_ecdsa",
        "id_ed25519",
        "*_key",
        "*_private",
    ]

    insecure_keys = []
    for pattern in ssh_key_patterns:
        result = run_on_host(
            host,
            f"find {input_path} -name '{pattern}' -type f 2>/dev/null",
        )

        if result.rc == 0 and result.stdout.strip():
            for key_file in result.stdout.strip().split("\n"):
                if not key_file.strip():
                    continue

                perm_result = run_on_host(
                    host,
                    f"stat -c '%a' {key_file} 2>/dev/null",
                )

                if perm_result.rc == 0:
                    perms = perm_result.stdout.strip()
                    # SSH keys should be 0600 (owner read/write only)
                    if perms != "600":
                        insecure_keys.append(f"{key_file} ({perms})")

    if not insecure_keys:
        tl.passed(
            "All SSH keys have proper permissions (0600)",
            f"Checked patterns: {', '.join(ssh_key_patterns)}\n"
            f"Path: {input_path}",
        )
    else:
        tl.failed(
            f"Found {len(insecure_keys)} SSH keys with incorrect permissions",
            f"Insecure keys:\n" + "\n".join(insecure_keys),
        )

    assert not insecure_keys, (
        f"SSH keys with incorrect permissions found: {insecure_keys}"
    )


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(3)
def test_sensitive_log_permissions(host):
    """NFT_OR_010: Verify sensitive log files have restricted permissions.

    Checks that orchestrator log files don't have world-readable permissions
    that could expose sensitive information.
    """
    tl = TestLogger("NFT: Sensitive log file permissions", "NFT_OR_010")

    config = load_test_config()
    log_path = config.get("log_path", "/var/log/omnia")

    # Check log directory permissions
    result = run_on_host(
        host,
        f"stat -c '%a' {log_path} 2>/dev/null",
    )

    if result.rc != 0:
        tl.skipped(f"Log directory not found: {log_path}")
        pytest.skip(f"Log directory not found: {log_path}")

    dir_perms = result.stdout.strip()
    # Log directory should not be world-writable
    is_safe = dir_perms[2] != "2" and dir_perms[2] != "7"  # No world write

    # Check log file permissions
    log_result = run_on_host(
        host,
        f"find {log_path} -name '*.log' -type f -exec stat -c '%a %n' {{}} \\; 2>/dev/null",
    )

    world_readable_logs = []
    if log_result.rc == 0 and log_result.stdout.strip():
        for line in log_result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                perms, log_file = parts[0], " ".join(parts[1:])
                # Check if world-readable (last digit is 4, 5, 6, or 7)
                if len(perms) == 3 and perms[2] in ["4", "5", "6", "7"]:
                    world_readable_logs.append(f"{log_file} ({perms})")

    all_ok = is_safe and not world_readable_logs

    if all_ok:
        tl.passed(
            "Log files have appropriate permissions",
            f"Log directory: {log_path} ({dir_perms})\n"
            f"No world-readable log files found",
        )
    else:
        issues = []
        if not is_safe:
            issues.append(f"Log directory has world-writable permissions: {dir_perms}")
        if world_readable_logs:
            issues.append(f"World-readable log files: {len(world_readable_logs)}")

        tl.failed(
            f"Log permission issues found: {len(issues)}",
            "\n".join(issues) + ("\n" + "\n".join(world_readable_logs) if world_readable_logs else ""),
        )

    assert all_ok, (
        f"Log permission issues: {issues if issues else 'None'}"
    )


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(4)
def test_vault_encryption_verification(host):
    """NFT_OR_011: Verify Ansible vault encryption is properly configured.

    Checks that vault-encrypted files have the proper vault header
    and that vault key files have restricted permissions.
    """
    tl = TestLogger("NFT: Ansible vault encryption verification", "NFT_OR_011")

    input_path = _get_input_path()
    cred_file = f"{input_path}/{CREDENTIALS_FILE_NAME}"
    vault_key_file = f"{input_path}/{CREDENTIALS_KEY_NAME}"

    # Check if credential file exists and is vault-encrypted
    cred_result = run_on_host(
        host,
        f"test -f {cred_file} && head -1 {cred_file} 2>/dev/null",
    )

    if cred_result.rc != 0:
        tl.skipped(f"Credential file not found: {cred_file}")
        pytest.skip(f"Credential file not found: {cred_file}")

    # Check for vault header
    has_vault_header = "$ANSIBLE_VAULT" in cred_result.stdout

    # Check vault key file permissions
    key_result = run_on_host(
        host,
        f"stat -c '%a' {vault_key_file} 2>/dev/null",
    )

    key_perms_ok = False
    if key_result.rc == 0:
        key_perms = key_result.stdout.strip()
        # Vault key should be 0600 (owner only)
        key_perms_ok = key_perms == "600"

    all_ok = has_vault_header and key_perms_ok

    if all_ok:
        tl.passed(
            "Vault encryption properly configured",
            f"Credential file: {cred_file} (vault encrypted)\n"
            f"Vault key: {vault_key_file} (permissions: {key_result.stdout.strip()})",
        )
    else:
        issues = []
        if not has_vault_header:
            issues.append(f"Credential file missing vault header")
        if not key_perms_ok:
            issues.append(f"Vault key has incorrect permissions: {key_result.stdout.strip() if key_result.rc == 0 else 'not found'}")

        tl.failed(
            f"Vault encryption issues: {len(issues)}",
            "\n".join(issues),
        )

    assert has_vault_header, "Credential file missing vault header"
    assert key_perms_ok, f"Vault key has incorrect permissions: {key_result.stdout.strip() if key_result.rc == 0 else 'not found'}"