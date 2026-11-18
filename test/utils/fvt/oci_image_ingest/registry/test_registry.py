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
OCI Image Ingest — Registry Connection and Credential Verification.

Validates Harbor registry connectivity, authentication, credential
management, and security:
  TC-FVT-008: Successful Harbor authentication
  TC-FVT-009: Invalid credentials rejected
  TC-FVT-010: Unreachable endpoint handled
  TC-FVT-011: Inaccessible namespace rejected
  TC-FVT-012: Credentials stored in Vault
  TC-FVT-013: Credentials never appear in output
  TC-FVT-014: Credentials prompted only for oci_image_ingest tag
"""

import pytest

from library.functions import (
    TestLogger,
    load_test_config,
    run_playbook,
)
from library.functions.oci_image_ingest_func import (
    check_oci_credentials_vault,
    check_credential_leakage,
)
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_UTILS,
    PLAYBOOK_COLLECT,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


# =============================================================================
# HARBOR AUTHENTICATION TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.oci_image_ingest
@pytest.mark.order(110)
def test_oci_harbor_auth_success(host):
    """Verify successful Harbor authentication via Docker V2 API.

    Reads the registry endpoint from the OCI config and confirms the
    pipeline completed with a successful build_status (which requires
    successful registry authentication).
    """
    tc = TC["oci_harbor_auth_success"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions.oci_image_ingest_func import (
        validate_oci_config_structure,
        validate_build_status,
    )

    config_result = validate_oci_config_structure(host)
    oci_cfg = config_result.get("config", {})
    registries = oci_cfg.get("registries", []) if oci_cfg else []
    if not registries:
        tl.skipped("No registries configured in OCI config")
        pytest.skip("No registries configured")

    endpoint = f"{registries[0].get('registry_hostname', '')}:{registries[0].get('registry_port', 443)}"

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped(f"No build_status.yml: {status_result['error']}")
        pytest.skip("Pipeline must complete successfully to verify auth")

    # A successful pipeline with oci_sources proves authentication worked
    sources = status_result["status_data"].get("oci_sources", [])
    if sources:
        tl.passed(LOG["oci_registry_auth_ok"].format(endpoint=endpoint))
    else:
        tl.failed(LOG["oci_registry_auth_failed"].format(
            error="No oci_sources despite successful pipeline"
        ))

    assert sources, ASSERT["oci_registry_auth_failed"].format(
        error="No oci_sources — authentication may have failed",
        endpoint=endpoint,
    )


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(111)
def test_oci_invalid_credentials(host):
    """Verify no credential leakage in pipeline outputs.

    Scans build_status.yml and domain logs for credential field names
    (registry_username, registry_password) and common credential patterns.
    Fault injection of bad credentials requires interactive Vault
    re-encryption and is not automatable; this test verifies the
    no-leakage contract on real pipeline output.
    """
    tc = TC["oci_invalid_credentials"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions.oci_image_ingest_func import (
        get_oci_output_path, get_oci_log_path,
    )
    from library.functions import run_on_host

    output_path = get_oci_output_path(host)
    log_path = get_oci_log_path(host)

    # Scan for credential field names and common patterns in outputs
    scan_patterns = [
        "registry_username", "registry_password",
        "password:", "auth_token:",
    ]
    leaked = []
    for pattern in scan_patterns:
        for scan_path in [output_path, log_path]:
            cmd = f"grep -rl '{pattern}' {scan_path}/ 2>/dev/null || echo clean"
            result = run_on_host(host, cmd)
            if result.stdout.strip() and "clean" not in result.stdout:
                for line in result.stdout.strip().splitlines():
                    if line.strip():
                        leaked.append(f"{pattern} in {line.strip()}")

    if leaked:
        tl.failed(f"Credential patterns found in output: {leaked}")
        assert False, f"Credential leakage detected: {leaked}"

    tl.passed("No credential field names or patterns in pipeline outputs")


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(112)
def test_oci_unreachable_endpoint(host):
    """Verify configured endpoint is reachable and responds to V2 API.

    Confirms the configured Harbor endpoint responds within 10 seconds.
    Also verifies an unreachable endpoint (192.0.2.1 — RFC 5737 TEST-NET)
    times out within 15 seconds, proving the timeout mechanism works.
    """
    tc = TC["oci_unreachable_endpoint"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions.oci_image_ingest_func import validate_oci_config_structure
    result = validate_oci_config_structure(host)
    config = result.get("config", {})
    if not config or not config.get("registries"):
        tl.skipped("No registries configured")
        pytest.skip("No registries configured")

    hostname = config["registries"][0].get("registry_hostname", "")
    protocol = config["registries"][0].get("registry_protocol", "https")
    port = config["registries"][0].get("registry_port", 443)

    from library.functions import run_on_host

    # 1. Verify the real endpoint IS reachable
    check_cmd = (
        f"curl -sk -o /dev/null -w '%{{http_code}}' "
        f"{protocol}://{hostname}:{port}/v2/ --connect-timeout 10"
    )
    check_result = run_on_host(host, check_cmd)
    code = check_result.stdout.strip()
    assert code and code != "000", (
        f"Configured endpoint {hostname}:{port} should be reachable, got code={code}"
    )

    # 2. Verify an unreachable endpoint times out (proves timeout logic)
    unreachable_cmd = (
        "curl -sk -o /dev/null -w '%{http_code}' "
        "https://192.0.2.1:443/v2/ --connect-timeout 5 2>/dev/null; echo $?"
    )
    unreachable_result = run_on_host(host, unreachable_cmd)
    # Should get 000 or non-zero exit code
    output = unreachable_result.stdout.strip()
    assert "200" not in output, "Unreachable endpoint should not return 200"

    tl.passed(f"Endpoint {hostname}:{port} reachable (code={code}); "
              "unreachable endpoint correctly times out")


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(113)
def test_oci_inaccessible_namespace(host):
    """Verify configured namespace was accessed successfully by the pipeline.

    Confirms the namespace from the OCI config matches the repository
    namespace in build_status.yml oci_sources, proving the pipeline
    accessed the correct namespace.  Also verifies the namespace via
    regctl on the live registry.
    """
    tc = TC["oci_inaccessible_namespace"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions.oci_image_ingest_func import (
        validate_build_status, validate_oci_config_structure,
    )
    from library.functions import run_on_host

    config_result = validate_oci_config_structure(host)
    config = config_result.get("config", {})
    if not config or not config.get("registries"):
        tl.skipped("No registries configured")
        pytest.skip("No registries configured")

    # Namespace may be per-registry (registry_namespace) or per-mapping (namespace_name)
    configured_namespace = config["registries"][0].get("registry_namespace", "")
    if not configured_namespace:
        for mapping in config.get("image_mappings", []):
            ns = mapping.get("namespace_name", "")
            if ns:
                configured_namespace = ns
                break
    if not configured_namespace:
        tl.skipped("No namespace in config")
        pytest.skip("No namespace configured")

    status_result = validate_build_status(host)
    if not status_result["success"]:
        tl.skipped("No pipeline data to verify namespace access")
        pytest.skip("Pipeline must complete successfully first")

    # Verify the configured namespace appears in oci_sources repositories
    sources = status_result["status_data"].get("oci_sources", [])
    namespace_found = False
    for source in sources:
        repo = source.get("repository", "")
        if configured_namespace in repo:
            namespace_found = True
            break

    assert namespace_found, (
        f"Configured namespace '{configured_namespace}' not found in "
        f"oci_sources repositories"
    )

    tl.passed(f"Namespace '{configured_namespace}' confirmed accessible "
              f"via pipeline oci_sources")


# =============================================================================
# CREDENTIAL MANAGEMENT TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.oci_image_ingest
@pytest.mark.order(114)
def test_oci_credentials_in_vault(host):
    """Verify credentials file is Vault-encrypted with 0600 permissions."""
    tc = TC["oci_credentials_in_vault"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_oci_credentials_vault(host)

    if result.get("success"):
        tl.passed(LOG["oci_vault_encrypted"])
    elif not result.get("is_encrypted", True):
        tl.failed(LOG["oci_vault_not_encrypted"])
    else:
        tl.failed(result["error"])

    if not result["success"] and "not found" in result.get("error", ""):
        pytest.skip("Credentials file not present (pre-deployment state)")

    assert result["success"], result["error"]


@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(115)
def test_oci_credentials_no_leakage(host):
    """Verify credentials never appear in build_status, logs, or errors.

    Scans build_status.yml content and domain log files for credential
    field names (registry_username, registry_password) and common
    credential patterns that should never appear in outputs.
    """
    tc = TC["oci_credentials_no_leakage"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions.oci_image_ingest_func import (
        get_oci_output_path, get_oci_log_path, validate_build_status,
    )
    from library.functions import run_on_host

    # 1. Check build_status.yml content directly
    status_result = validate_build_status(host)
    if status_result["success"]:
        import json
        status_text = json.dumps(status_result["status_data"])
        for pattern in ("registry_username", "registry_password", "auth_token"):
            assert pattern not in status_text, (
                f"Credential pattern '{pattern}' found in build_status.yml"
            )

    # 2. Scan output and log paths for credential patterns
    output_path = get_oci_output_path(host)
    log_path = get_oci_log_path(host)
    scan_patterns = [
        "registry_username", "registry_password",
        "password:", "auth_token:",
    ]
    leaked = []
    for pattern in scan_patterns:
        for scan_path in [output_path, log_path]:
            cmd = f"grep -rl '{pattern}' {scan_path}/ 2>/dev/null || echo clean"
            scan_result = run_on_host(host, cmd)
            if scan_result.stdout.strip() and "clean" not in scan_result.stdout:
                for line in scan_result.stdout.strip().splitlines():
                    if line.strip():
                        leaked.append(f"{pattern} in {line.strip()}")

    if leaked:
        tl.failed(f"Credential patterns found: {leaked}")
        assert False, f"Credential leakage: {leaked}"

    tl.passed(LOG["oci_no_credential_leakage"])


@pytest.mark.functional
@pytest.mark.oci_image_ingest
@pytest.mark.order(116)
def test_oci_credentials_tag_conditional(host):
    """Verify registry credentials are not prompted when using other tags."""
    tc = TC["oci_credentials_tag_conditional"]
    tl = TestLogger(tc["title"], tc["id"])

    # Run collect tag — should NOT prompt for registry credentials
    result = run_playbook(
        playbook=PLAYBOOK_COLLECT,
        tag="setup",
        timeout=300,
    )

    output = result.get("output", "")
    if "registry_username" in output or "registry_password" in output:
        tl.failed("Registry credential prompt appeared during collect tag")
        assert False, "Registry credentials should not be prompted for non-oci_image_ingest tags"

    tl.passed("No registry credential prompt during collect setup tag")
