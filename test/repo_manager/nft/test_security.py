# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Repo Manager credential, key, log, and certificate security checks."""

import pytest

from omnia_auto import run_on_host
from library.functions import TestLogger
from library.vars.common_vars import (
    INPUT_FILES,
    _get_base_path,
    _get_input_path,
    _get_pulp_certs_dir,
)


def _mode_is_private(mode):
    """Return whether group/world permissions are absent."""
    return mode is not None and mode & 0o077 == 0


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(1)
def test_credentials_are_encrypted_and_private(host):
    """RM_NFT_003: Credentials are vaulted and credential files are private."""
    test_log = TestLogger(
        "NFT: encrypted private credentials", "RM_NFT_003"
    )
    input_path = _get_input_path()
    credential_path = f"{input_path}/{INPUT_FILES['repo_manager_credentials']}"
    key_path = f"{input_path}/.repo_manager_config_credentials_key"
    credential_file = host.file(credential_path)
    key_file = host.file(key_path)

    failures = []
    if not credential_file.exists:
        failures.append(f"Missing credential file: {credential_path}")
    else:
        if not credential_file.content_string.startswith("$ANSIBLE_VAULT;"):
            failures.append("Credential file is not Ansible Vault encrypted")
        if not _mode_is_private(credential_file.mode):
            failures.append(
                f"Credential mode is {credential_file.mode:o}, expected 0600"
            )
    if not key_file.exists:
        failures.append(f"Missing credential key: {key_path}")
    elif not _mode_is_private(key_file.mode):
        failures.append(f"Credential-key mode is {key_file.mode:o}, expected 0600")

    if failures:
        test_log.failed("Credential protection check failed", "\n".join(failures))
    else:
        test_log.passed(
            "Credentials are encrypted and private",
            "Credential and vault-key modes deny all group/world access.",
        )
    assert not failures, "; ".join(failures)


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(2)
def test_private_keys_and_log_directories_are_restricted(host):
    """RM_NFT_004: Pulp private keys and Repo Manager logs deny public access."""
    test_log = TestLogger(
        "NFT: private keys and log permissions", "RM_NFT_004"
    )
    protected_paths = [
        f"{_get_pulp_certs_dir()}/pulp_webserver.key",
        f"{_get_pulp_certs_dir()}/token_private_key.pem",
        f"{_get_base_path()}/log",
        "/var/log/omnia/repo_manager",
    ]
    failures = []
    for path in protected_paths:
        remote_file = host.file(path)
        if not remote_file.exists:
            failures.append(f"Missing protected path: {path}")
        elif not _mode_is_private(remote_file.mode):
            failures.append(f"Overly permissive mode {remote_file.mode:o}: {path}")

    if failures:
        test_log.failed("Protected-path permissions are unsafe", "\n".join(failures))
    else:
        test_log.passed(
            "Private keys and logs have restricted permissions",
            f"Validated {len(protected_paths)} protected paths.",
        )
    assert not failures, "; ".join(failures)


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(3)
def test_pulp_tls_certificate_is_current(host):
    """RM_NFT_005: The Pulp TLS certificate remains valid for at least one day."""
    test_log = TestLogger(
        "NFT: Pulp TLS certificate validity", "RM_NFT_005"
    )
    certificate_path = f"{_get_pulp_certs_dir()}/pulp_webserver.crt"
    result = run_on_host(
        host,
        f"openssl x509 -checkend 86400 -noout -in {certificate_path}",
    )

    if result.rc == 0:
        test_log.passed(
            "Pulp TLS certificate is current",
            "The certificate is valid for more than the next 24 hours.",
        )
    else:
        test_log.failed(
            "Pulp TLS certificate is expired or near expiry",
            f"Certificate: {certificate_path}",
        )
    assert result.rc == 0, (
        "Pulp TLS certificate is invalid or expires within 24 hours"
    )
