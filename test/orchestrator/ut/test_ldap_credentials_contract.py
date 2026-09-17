# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Contracts for test-owned LDAP credentials and Slurm login verification."""

from pathlib import Path

import pytest

from ut.source_loader import TEST_ROOT


pytestmark = pytest.mark.unit


def _read(relative_path):
    return (Path(TEST_ROOT) / relative_path).read_text(encoding="utf-8")


def test_setup_env_keeps_ldap_test_credentials_out_of_product_inputs():
    """ORCH_UT_100: LDAP test secrets belong only to test_creds.yml."""
    setup = _read("setup_env.sh")
    credential_block = setup[
        setup.index("_write_ldap_test_credentials_stdin()"):
        setup.index("# Read a field from the domain creds file")
    ]
    assert "--set-ldap-test-creds" in setup
    assert "--ldap-test-creds-stdin" in setup
    assert '--creds-path "$CREDS_FILE"' in credential_block
    assert '--key-path "$CREDS_KEY"' in credential_block
    assert "_domain_creds_path" not in credential_block
    assert "orchestrator_credentials.yml" not in credential_block


def test_ldap_checks_load_only_framework_credentials():
    """ORCH_UT_101: Slurm LDAP checks do not read product credentials."""
    source = _read("library/functions/slurm_func.py")
    ldap_block = source[
        source.index("# LDAP AUTHENTICATION TESTS"):
        source.index("# GPU TESTING")
    ]
    assert "load_test_credentials()" in ldap_block
    assert "load_test_config()" not in ldap_block
    assert "orchestrator_credentials" not in ldap_block


def test_ldap_password_is_supplied_through_a_temporary_mode_0600_file():
    """ORCH_UT_102: LDAP passwords never appear in an ssh command line."""
    source = _read("library/functions/slurm_func.py")
    ldap_block = source[
        source.index("# LDAP AUTHENTICATION TESTS"):
        source.index("# GPU TESTING")
    ]
    assert "sshpass" in ldap_block
    assert '"-f"' in ldap_block
    assert "chmod 0600" in ldap_block
    assert "os.unlink(local_path)" in ldap_block
    assert '"-p"' not in ldap_block
    assert "SSHPASS=" not in ldap_block


def test_ldap_login_opens_and_closes_a_slurm_job_access_window():
    """ORCH_UT_103: Interactive login occurs only while its job is active."""
    source = _read("library/functions/slurm_func.py")
    login_block = source[
        source.index("def check_ldap_user_login("):
        source.index("def check_ldap_job_submission(")
    ]
    assert "--wrap='sleep 120'" in login_block
    assert "state.upper() == \"RUNNING\"" in login_block
    assert "with _target_password_file" in login_block
    assert "finally:" in login_block
    assert "scancel {job_id}" in login_block


def test_ldap_job_submission_uses_the_configured_directory_identity():
    """ORCH_UT_104: Job submission changes identity without product secrets."""
    source = _read("library/functions/slurm_func.py")
    submission = source[source.index("def check_ldap_job_submission("):]
    assert "sudo -iu {username} sbatch --parsable" in submission
    assert "orchestrator_credentials" not in submission
    assert "openldap_db_password" not in submission


def test_missing_ldap_test_credentials_skip_without_prompting():
    """ORCH_UT_105: Unconfigured LDAP checks remain non-interactive."""
    source = _read("library/functions/slurm_func.py")
    ldap_block = source[
        source.index("# LDAP AUTHENTICATION TESTS"):
        source.index("# GPU TESTING")
    ]
    assert '"skipped": True' in ldap_block
    assert "--set-ldap-test-creds" in ldap_block
    assert "input(" not in ldap_block
    assert "getpass" not in ldap_block
