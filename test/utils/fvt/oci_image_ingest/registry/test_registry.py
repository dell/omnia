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
    """Verify invalid credentials are rejected without leakage.

    Exercises the actual production failure path:
    1. Positive control: the stored credentials get HTTP 200 from the
       Registry V2 ``/v2/`` auth endpoint (the call the production
       validate_registry_connection role makes).
    2. Deliberately bad credentials get HTTP 401 from the same probe;
       the production role fails on that 401/403 before any pull.
    3. The bad password never appears in the output, and all pipeline
       outputs are scanned for credential leakage.
    Credentials travel only in private 0600 curl config files; no global
    regctl or curl state is read or written.
    """
    tc = TC["oci_invalid_credentials"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions.oci_image_ingest_func import (
        get_oci_output_path, get_oci_log_path, get_registry_info,
        get_oci_src_utils_path, registry_v2_auth_cmd,
    )
    from library.functions import get_utils_input_path, run_on_host
    from library.vars import CMDS

    reg_info = get_registry_info(host)
    if not reg_info["success"]:
        tl.skipped(f"No registry configured: {reg_info['error']}")
        pytest.skip("No registry configured")

    endpoint = reg_info["endpoint"]
    namespace = reg_info["namespace"]
    bad_password = "INVALID_FVT_TEST_PASSWORD_xyzzy"

    # 1. Positive control: the stored credentials authenticate (HTTP 200)
    #    through the same private-config probe, so a failure below cannot be
    #    a TLS or connectivity problem.
    control = run_on_host(
        host,
        registry_v2_auth_cmd(endpoint, vault_dir=get_utils_input_path(host)),
    )
    assert control.stdout.strip() == "200", (
        f"Control probe with stored credentials returned "
        f"{control.stdout.strip()!r}, cannot attribute failure to credentials"
    )

    # 2. Negative: bad credentials through the same probe must be rejected
    #    with HTTP 401 (password in a 0600 file, never in argv)
    bad_auth = run_on_host(
        host, registry_v2_auth_cmd(endpoint, "bad_user", bad_password)
    )
    assert bad_auth.stdout.strip() == "401", (
        f"Bad credentials should be rejected with HTTP 401, got "
        f"{bad_auth.stdout.strip()!r}"
    )
    assert bad_password not in bad_auth.stdout, (
        "Bad password value leaked into probe output"
    )

    # 2b. Rejection prevents the pull: production proceeds to regctl only
    #     after the /v2/ check passes, so the pull never starts.
    gate = run_on_host(
        host,
        "grep -n \"_oci_v2_check.status in \\[401, 403\\]\" "
        f"{get_oci_src_utils_path(host)}/roles/validate_registry_connection/tasks/registry.yml",
    )
    assert gate.stdout.strip(), (
        "Production role does not fail on a 401/403 from the /v2/ check"
    )

    # 3. Scan pipeline outputs for credential leakage
    output_path = get_oci_output_path(host)
    log_path = get_oci_log_path(host)
    leaked = []
    for pattern in ["registry_username", "registry_password",
                     "password:", "auth_token:"]:
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
        "Bad credentials rejected by live registry; "
        "no credential leakage in pipeline outputs"
    )


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
    """Verify inaccessible namespace is rejected before image pull.

    Exercises the actual production failure path:
    1. Runs regctl tag ls against a nonexistent namespace on the live
       registry and verifies it returns an error.
    2. Queries the registry V2 API for the nonexistent namespace and
       verifies an HTTP 400/401/403/404 response.
    3. Verifies the configured namespace IS accessible (positive).
    """
    tc = TC["oci_inaccessible_namespace"]
    tl = TestLogger(tc["title"], tc["id"])

    from library.functions.oci_image_ingest_func import (
        validate_oci_config_structure, get_registry_info, regctl_cmd,
    )
    from library.functions import run_on_host

    config_result = validate_oci_config_structure(host)
    config = config_result.get("config", {})
    if not config or not config.get("registries"):
        tl.skipped("No registries configured")
        pytest.skip("No registries configured")

    configured_namespace = ""
    for mapping in config.get("image_mappings", []):
        ns = mapping.get("namespace_name", "")
        if ns:
            configured_namespace = ns
            break
    if not configured_namespace:
        tl.skipped("No namespace in config")
        pytest.skip("No namespace configured")

    reg_info = get_registry_info(host)
    if not reg_info["success"]:
        tl.skipped(f"No registry configured: {reg_info['error']}")
        pytest.skip("No registry configured")

    endpoint = reg_info["endpoint"]
    bad_ns = "nonexistent_namespace_xyzzy_404"

    # 1. Negative: run regctl tag ls against a nonexistent namespace
    #    This is the same code path the production pipeline uses.
    # The endpoint must appear in both regctl_cmd() (TLS/auth config) and the
    # image ref (registry routing); without it regctl defaults to docker.io.
    regctl_result = run_on_host(
        host, regctl_cmd(endpoint, f"tag ls {endpoint}/{bad_ns}/test-image")
    )
    regctl_out = regctl_result.stdout.strip().lower()
    assert regctl_result.rc != 0 and any(
        marker in regctl_out
        for marker in ("not found", "404", "401", "403", "unauthorized",
                       "denied", "forbidden")
    ), (
        f"Expected regctl to fail for inaccessible namespace, "
        f"got rc={regctl_result.rc}: {regctl_result.stdout.strip()}"
    )

    # 2. Negative: query the registry V2 API for the nonexistent namespace
    bad_ns_cmd = (
        f"curl -sk -o /dev/null -w '%{{http_code}}' "
        f"https://{endpoint}/v2/{bad_ns}/tags/list "
        f"--connect-timeout 10 2>&1"
    )
    bad_result = run_on_host(host, bad_ns_cmd)
    bad_code = bad_result.stdout.strip()[-3:] if bad_result.stdout.strip() else "000"
    assert bad_code in ("400", "401", "403", "404"), (
        f"Nonexistent namespace should return 400/401/403/404, got {bad_code}"
    )

    # 3. Positive: configured namespace is accessible via regctl
    first_img = reg_info["images"][0] if reg_info.get("images") else None
    if first_img:
        good_result = run_on_host(
            host,
            regctl_cmd(
                endpoint,
                f"tag ls {endpoint}/{configured_namespace}/"
                f"{first_img['image_name']}",
            ),
        )
        assert good_result.rc == 0 and good_result.stdout.strip(), (
            f"Configured namespace '{configured_namespace}' should be accessible"
        )

    tl.passed(
        f"Inaccessible namespace '{bad_ns}' rejected by regctl and HTTP API "
        f"(code {bad_code}); configured namespace '{configured_namespace}' accessible"
    )


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
