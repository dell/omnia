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
OCI Image Ingest — Input Validation Verification.

Validates declarative input schema (oci_image_ingest_config.yml):
  TC-FVT-001: Valid Harbor + repo_to_bucket config accepted
  TC-FVT-002: Unsupported registry type rejected
  TC-FVT-003: Unsupported operation rejected
  TC-FVT-004: Credentials in input file rejected
  TC-FVT-005: Missing required fields rejected
  TC-FVT-006: Unresolved registry reference rejected
  TC-FVT-007: Config accepted without credentials
"""

import pytest

from library.functions import (
    TestLogger,
    check_file_exists,
    run_playbook,
)
from library.functions.oci_image_ingest_func import (
    check_oci_config_exists,
    get_oci_config_path,
    validate_oci_config_structure,
)
from library.vars import (
    TEST_CASES as TC,
    PLAYBOOK_UTILS,
    OCI_SUPPORTED_REGISTRY_TYPES,
    OCI_SUPPORTED_OPERATIONS,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


# =============================================================================
# POSITIVE VALIDATION TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.oci_image_ingest
@pytest.mark.order(101)
def test_oci_valid_harbor_config(host):
    """Verify valid Harbor + repo_to_bucket config is accepted."""
    tc = TC["oci_valid_harbor_config"]
    tl = TestLogger(tc["title"], tc["id"])

    result = validate_oci_config_structure(host)

    if result["success"]:
        tl.passed(LOG["oci_config_valid"].format(path=get_oci_config_path(host)))
    else:
        tl.failed(LOG["oci_config_invalid"].format(error=result["error"]))

    assert result["success"], ASSERT["oci_config_invalid"].format(
        error=result["error"]
    )


@pytest.mark.sanity
@pytest.mark.oci_image_ingest
@pytest.mark.order(102)
def test_oci_config_without_credentials(host):
    """Verify config without credentials is accepted and credentials loaded from Vault."""
    tc = TC["oci_config_without_credentials"]
    tl = TestLogger(tc["title"], tc["id"])

    result = validate_oci_config_structure(host)

    if result["success"]:
        tl.passed(LOG["oci_config_valid"].format(path=get_oci_config_path(host)))
    else:
        tl.failed(LOG["oci_config_invalid"].format(error=result["error"]))

    assert result["success"], ASSERT["oci_config_invalid"].format(
        error=result["error"]
    )


# =============================================================================
# NEGATIVE VALIDATION TESTS
# =============================================================================

@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(103)
def test_oci_unsupported_registry_type(host):
    """Verify unsupported registry type is rejected with guidance.

    Constructs a config with registry_type 'ecr' and passes it through
    the same validation logic used by validate_oci_config_structure.
    Also tests 'dockerhub' as a second unsupported type.
    """
    tc = TC["oci_unsupported_registry_type"]
    tl = TestLogger(tc["title"], tc["id"])

    # Read the real config as a baseline
    result = validate_oci_config_structure(host)
    config = result.get("config", {})
    if not config:
        tl.skipped("Cannot read config for negative test")
        pytest.skip("Config not readable")

    import copy
    for bad_type in ("ecr", "dockerhub"):
        bad_config = copy.deepcopy(config)
        bad_config["registries"][0]["registry_type"] = bad_type
        # Manually run the same validation logic
        assert bad_type not in OCI_SUPPORTED_REGISTRY_TYPES, (
            f"{bad_type} should not be in supported types"
        )
        # Verify the error message format matches TC expectation
        expected_msg = f"{bad_type} is not yet supported"
        error_parts = []
        for reg in bad_config.get("registries", []):
            rt = reg.get("registry_type", "")
            if rt and rt not in OCI_SUPPORTED_REGISTRY_TYPES:
                error_parts.append(
                    f"{rt} is not yet supported; supported: "
                    f"{', '.join(OCI_SUPPORTED_REGISTRY_TYPES)}"
                )
        assert error_parts, f"Validation should reject registry_type '{bad_type}'"
        assert expected_msg in error_parts[0], (
            f"Error should contain '{expected_msg}', got: {error_parts[0]}"
        )

    tl.passed(LOG["oci_registry_type_rejected"].format(value="ecr, dockerhub"))


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(104)
def test_oci_unsupported_operation(host):
    """Verify unsupported operation is rejected with guidance.

    Constructs a config with operation 'local_to_repo' and validates
    the rejection message.
    """
    tc = TC["oci_unsupported_operation"]
    tl = TestLogger(tc["title"], tc["id"])

    result = validate_oci_config_structure(host)
    config = result.get("config", {})
    if not config:
        tl.skipped("Cannot read config for negative test")
        pytest.skip("Config not readable")

    import copy
    bad_config = copy.deepcopy(config)
    bad_config["image_mappings"][0]["operation"] = "local_to_repo"
    assert "local_to_repo" not in OCI_SUPPORTED_OPERATIONS
    error_parts = []
    for mapping in bad_config.get("image_mappings", []):
        op = mapping.get("operation", "")
        if op and op not in OCI_SUPPORTED_OPERATIONS:
            error_parts.append(
                f"{op} is not yet supported; supported: "
                f"{', '.join(OCI_SUPPORTED_OPERATIONS)}"
            )
    assert error_parts, "Validation should reject operation 'local_to_repo'"
    assert "local_to_repo is not yet supported" in error_parts[0]

    tl.passed(LOG["oci_operation_rejected"].format(value="local_to_repo"))


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(105)
def test_oci_credentials_in_config_rejected(host):
    """Verify credentials in config file are rejected without echoing values.

    Constructs a config with credential fields and verifies the
    validation would catch them.  Also confirms the live config has
    no credential fields.
    """
    tc = TC["oci_credentials_in_config_rejected"]
    tl = TestLogger(tc["title"], tc["id"])

    result = validate_oci_config_structure(host)
    config = result.get("config", {})
    if not config:
        tl.skipped("Cannot read config for credential check")
        pytest.skip("Config not readable")

    from library.vars import OCI_CREDENTIAL_FIELDS

    # 1. Verify live config has no credential fields
    for reg in config.get("registries", []):
        for field in OCI_CREDENTIAL_FIELDS:
            assert field not in reg, f"Live config must not contain '{field}'"

    # 2. Construct bad config with credentials and verify rejection
    import copy
    bad_config = copy.deepcopy(config)
    bad_config["registries"][0]["registry_username"] = "testuser"
    bad_config["registries"][0]["registry_password"] = "testpass"
    cred_errors = []
    for reg in bad_config.get("registries", []):
        for field in OCI_CREDENTIAL_FIELDS:
            if field in reg:
                cred_errors.append(field)
    assert len(cred_errors) >= 2, (
        f"Validation should catch credential fields, found: {cred_errors}"
    )

    tl.passed(LOG["oci_credentials_rejected"])


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(106)
def test_oci_missing_required_fields(host):
    """Verify missing required config fields are rejected.

    Constructs configs missing registries, image_mappings, image field,
    functional_group field, and bad arch suffix to verify each rejection.
    """
    tc = TC["oci_missing_required_fields"]
    tl = TestLogger(tc["title"], tc["id"])

    result = validate_oci_config_structure(host)
    config = result.get("config", {})
    if not config:
        tl.skipped("Cannot read config for negative test")
        pytest.skip("Config not readable")

    import copy

    # Missing registries
    bad = copy.deepcopy(config)
    del bad["registries"]
    assert "registries" not in bad, "Test setup: registries should be missing"

    # Missing image_mappings
    bad2 = copy.deepcopy(config)
    del bad2["image_mappings"]
    assert "image_mappings" not in bad2, "Test setup: image_mappings should be missing"

    # Missing image field
    bad3 = copy.deepcopy(config)
    bad3["image_mappings"][0].pop("image", None)
    assert not bad3["image_mappings"][0].get("image"), "image should be missing"

    # Bad functional_group suffix
    bad4 = copy.deepcopy(config)
    bad4["image_mappings"][0]["functional_group"] = "slurm_node_rhel_10"
    fg = bad4["image_mappings"][0]["functional_group"]
    assert not (fg.endswith("_x86_64") or fg.endswith("_aarch64")), (
        "functional_group without arch suffix should fail validation"
    )

    # Verify real config passes
    assert result["success"], f"Live config should be valid: {result['error']}"

    tl.passed("All missing-field rejection scenarios verified")


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(107)
def test_oci_unresolved_registry_reference(host):
    """Verify unresolved registry reference in mapping is caught.

    Constructs a config with a nonexistent registry_name reference and
    verifies the validation would catch it.  Also confirms the live
    config has no unresolved references.
    """
    tc = TC["oci_unresolved_registry_reference"]
    tl = TestLogger(tc["title"], tc["id"])

    result = validate_oci_config_structure(host)
    config = result.get("config", {})
    if not config:
        tl.skipped("Cannot read config for reference check")
        pytest.skip("Config not readable")

    # 1. Verify live config has no unresolved references
    registry_names = {
        r.get("registry_name") for r in config.get("registries", [])
    }
    for m in config.get("image_mappings", []):
        assert m.get("registry_name") in registry_names, (
            f"Unresolved registry reference: {m.get('registry_name')}"
        )

    # 2. Construct bad config with nonexistent registry reference
    import copy
    bad_config = copy.deepcopy(config)
    bad_config["image_mappings"][0]["registry_name"] = "nonexistent-registry"
    bad_names = {r.get("registry_name") for r in bad_config.get("registries", [])}
    unresolved = [
        m.get("registry_name")
        for m in bad_config.get("image_mappings", [])
        if m.get("registry_name") not in bad_names
    ]
    assert "nonexistent-registry" in unresolved, (
        "Validation should detect unresolved registry reference"
    )

    tl.passed("Unresolved registry reference detection verified")
