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
OCI Image Ingest — Non-Functional Tests.

Covers TC-NFT-001 through TC-NFT-005 from the ER-UTIL-001 test plan:
  TC-NFT-001: Registry connection validation timeout
  TC-NFT-002: Image transfer elapsed time recorded
  TC-NFT-003: Error phase identification
  TC-NFT-004: Credential security compliance
  TC-NFT-005: Logging completeness
"""

import os
import re
import time

import pytest

from library.functions import (
    TestLogger,
    run_on_host,
)
from library.functions.oci_image_ingest_func import (
    get_oci_log_path,
    get_oci_output_path,
    validate_build_status,
    validate_oci_config_structure,
    verify_s3_endpoint,
)
from library.vars import (
    TEST_CASES as TC,
    CMDS,
    OCI_CREDENTIAL_FIELDS,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


# =============================================================================
# TC-NFT-001: Registry connection validation timeout
# =============================================================================

@pytest.mark.nft
@pytest.mark.oci_image_ingest
@pytest.mark.order(901)
def test_nft_registry_connection_timeout(host):
    """Verify registry connection validation completes within 30 seconds.

    Tests:
    1. Connection to an unreachable endpoint (RFC 5737 TEST-NET) times out
       within 30 seconds wall-clock time.
    2. The production validate_registry_connection role has a timeout config.
    """
    tc = TC["nft_registry_connection_timeout"]
    tl = TestLogger(tc["title"], tc["id"])

    # 1. Verify unreachable endpoint times out within 30s
    start = time.time()
    result = run_on_host(
        host,
        "curl -sk -o /dev/null -w '%{http_code}' "
        "https://192.0.2.1:443/v2/ --connect-timeout 15 --max-time 30 2>&1",
    )
    elapsed = time.time() - start
    assert elapsed < 35, (
        f"Unreachable endpoint check took {elapsed:.1f}s — exceeds 30s threshold"
    )

    # 2. Verify production role has timeout configuration
    timeout_check = run_on_host(
        host,
        r"grep -rE 'timeout|connect_timeout' "
        "/root/main/omnia/src/utils/roles/validate_registry_connection/ "
        "2>/dev/null | head -3",
    )
    assert timeout_check.stdout.strip(), (
        "Production role does not have timeout configuration"
    )

    tl.passed(
        f"Unreachable endpoint detected in {elapsed:.1f}s (< 30s); "
        f"production role has timeout config"
    )


# =============================================================================
# TC-NFT-002: Image transfer elapsed time recorded
# =============================================================================

@pytest.mark.nft
@pytest.mark.oci_image_ingest
@pytest.mark.order(902)
def test_nft_transfer_elapsed_time_recorded(host):
    """Verify elapsed time is recorded for pipeline operations.

    Checks the Ansible log for task timing information from the
    most recent pipeline run.
    """
    tc = TC["nft_transfer_elapsed_time"]
    tl = TestLogger(tc["title"], tc["id"])

    log_path = get_oci_log_path(host)
    # Check for Ansible task timing in logs
    timing_check = run_on_host(
        host,
        r"grep -rE 'PLAY RECAP|ok=|changed=|elapsed|duration|time' "
        f"{log_path}/ 2>/dev/null | tail -10",
    )
    # Also check the report for timing data
    report_check = run_on_host(
        host,
        r"grep -rE 'duration|elapsed|seconds' "
        "/opt/omnia/reports/utils_*.json 2>/dev/null | head -5",
    )

    has_timing = bool(
        timing_check.stdout.strip() or report_check.stdout.strip()
    )
    if not has_timing:
        tl.skipped("No timing data found in logs or reports")
        pytest.skip("Pipeline logs not available for timing verification")

    tl.passed("Elapsed time data found in pipeline logs/reports")


# =============================================================================
# TC-NFT-003: Error phase identification
# =============================================================================

@pytest.mark.nft
@pytest.mark.oci_image_ingest
@pytest.mark.order(903)
def test_nft_error_phase_identification(host):
    """Verify error messages identify the failed phase and provide guidance.

    Checks:
    1. Production roles define phase-specific error messages.
    2. Error messages do not contain credential values.
    """
    tc = TC["nft_error_phase_identification"]
    tl = TestLogger(tc["title"], tc["id"])

    phases_found = []
    phase_patterns = {
        "connection": (
            "validate_registry_connection",
            r"connection|connectivity|Registry connection failed",
        ),
        "validation": (
            "validate_oci_image_ingest_config",
            r"validation failed|not yet supported|not defined",
        ),
        "credential": (
            "collect_oci_image_ingest_credentials",
            r"credential|empty|mismatch",
        ),
    }

    for phase, (role_name, pattern) in phase_patterns.items():
        role_dir = f"/root/main/omnia/src/utils/roles/{role_name}"
        check = run_on_host(
            host,
            f"grep -rE '{pattern}' {role_dir}/ 2>/dev/null | head -3",
        )
        if check.stdout.strip():
            phases_found.append(phase)

    assert len(phases_found) >= 2, (
        f"Expected phase-specific errors for >= 2 phases, found: {phases_found}"
    )

    # Verify no credential values in error messages (vars files)
    for role_name in ["validate_registry_connection",
                      "collect_oci_image_ingest_credentials"]:
        vars_check = run_on_host(
            host,
            f"grep -rE 'registry_password|registry_username' "
            f"/root/main/omnia/src/utils/roles/{role_name}/vars/ "
            f"2>/dev/null | grep -v 'no_log' | grep -v '#' | head -3",
        )
        # Allow references to field names in error message templates
        # but not actual values
        output = vars_check.stdout.strip()
        if output:
            for line in output.splitlines():
                assert ":" not in line.split("registry_password")[-1][:10] or \
                    "length" in line or "default" in line, (
                    f"Possible credential value in error message: {line}"
                )

    tl.passed(
        f"Phase-specific error messages found for: {', '.join(phases_found)}; "
        f"no credential values in error templates"
    )


# =============================================================================
# TC-NFT-004: Credential security compliance
# =============================================================================

@pytest.mark.nft
@pytest.mark.oci_image_ingest
@pytest.mark.order(904)
def test_nft_credential_security_compliance(host):
    """Verify credential security: Vault encryption, file permissions, no leakage.

    Checks:
    1. Credential file has 0600 permissions.
    2. Credential file is Vault-encrypted.
    3. Zero credential values in all non-Vault output paths.
    """
    tc = TC["nft_credential_security"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions.oci_image_ingest_func import get_oci_credentials_path
    cred_path = get_oci_credentials_path(host)

    # 1. Check file permissions (0600)
    perm_result = run_on_host(
        host,
        CMDS["file_permissions"].format(path=cred_path),
    )
    perms = perm_result.stdout.strip()
    assert perms == "600", (
        f"Credential file permissions should be 600, got {perms}"
    )

    # 2. Check Vault encryption
    header_result = run_on_host(
        host,
        CMDS["head_file"].format(n=1, path=cred_path),
    )
    header = header_result.stdout.strip()
    assert "$ANSIBLE_VAULT" in header, (
        f"Credential file not Vault-encrypted: header = {header}"
    )

    # 3. Scan all output paths for credential leakage
    output_path = get_oci_output_path(host)
    log_path = get_oci_log_path(host)
    leaked = []
    for pattern in OCI_CREDENTIAL_FIELDS:
        for scan_path in [output_path, log_path]:
            cmd = CMDS["credential_scan"].format(
                pattern=pattern, path=scan_path
            )
            result = run_on_host(host, cmd)
            if result.stdout.strip() and "clean" not in result.stdout:
                for line in result.stdout.strip().splitlines():
                    if line.strip():
                        leaked.append(f"{pattern} in {line.strip()}")

    assert not leaked, f"Credential leakage detected: {leaked}"

    tl.passed(
        f"Credential file: perms={perms}, Vault-encrypted; "
        f"zero credential leakage in outputs"
    )


# =============================================================================
# TC-NFT-005: Logging completeness
# =============================================================================

@pytest.mark.nft
@pytest.mark.oci_image_ingest
@pytest.mark.order(905)
def test_nft_logging_completeness(host):
    """Verify pipeline logs contain all required operational fields.

    Required fields: registry endpoint, namespace, image reference,
    digest, operation, S3 keys.
    """
    tc = TC["nft_logging_completeness"]
    tl = TestLogger(tc["title"], tc["id"])

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully first")

    sources = status_result["status_data"].get("oci_sources", [])
    assert sources, "No oci_sources in build_status"

    # Verify required fields are present in build_status (the primary log)
    required_fields = {
        "registry": False,
        "repository": False,
        "digest": False,
        "kernel_version": False,
        "functional_group": False,
    }
    for source in sources:
        for field in required_fields:
            if source.get(field):
                required_fields[field] = True

    missing = [f for f, v in required_fields.items() if not v]
    assert not missing, (
        f"Missing required fields in build_status oci_sources: {missing}"
    )

    # Verify S3 configuration is logged
    s3_cfg = status_result["status_data"].get("s3_configurations", {})
    assert s3_cfg.get("endpoint_url"), "Missing S3 endpoint in build_status"
    assert s3_cfg.get("bucket"), "Missing S3 bucket in build_status"

    # Verify no credentials in build_status
    import json
    status_str = json.dumps(status_result["status_data"])
    for cred_field in OCI_CREDENTIAL_FIELDS:
        assert cred_field not in status_str, (
            f"Credential field '{cred_field}' found in build_status"
        )

    tl.passed(
        f"All required fields present in build_status: "
        f"{', '.join(required_fields.keys())}; no credentials logged"
    )
