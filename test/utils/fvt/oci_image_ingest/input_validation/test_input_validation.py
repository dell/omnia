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

Validates declarative input schema (oci_image_ingest_config.yml) by invoking
the production validate_oci_image_ingest_config.run_validation() entry point:
  TC-FVT-001: Valid Harbor + repo_to_bucket config accepted
  TC-FVT-002: Unsupported registry type rejected
  TC-FVT-003: Unsupported operation rejected
  TC-FVT-004: Credentials in input file rejected
  TC-FVT-005: Missing required fields rejected
  TC-FVT-006: Unresolved registry reference rejected
  TC-FVT-007: Config accepted without credentials
"""

import copy
import pytest

from library.functions import (
    TestLogger,
    run_on_host,
)
from library.functions.oci_image_ingest_func import (
    get_oci_config_path,
    validate_oci_config_structure,
    run_production_validation,
)
from library.vars import (
    TEST_CASES as TC,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


def _load_live_config(host):
    """Load the live oci_image_ingest_config.yml as a Python dict."""
    result = validate_oci_config_structure(host)
    config = result.get("config", {})
    if not config:
        pytest.skip("Cannot read config for negative test")
    return config


# =============================================================================
# POSITIVE VALIDATION TESTS
# =============================================================================

@pytest.mark.sanity
@pytest.mark.oci_image_ingest
@pytest.mark.order(101)
def test_oci_valid_harbor_config(host):
    """Verify valid Harbor + repo_to_bucket config is accepted by production validator."""
    tc = TC["oci_valid_harbor_config"]
    tl = TestLogger(tc["title"], tc["id"])

    config = _load_live_config(host)
    result = run_production_validation(host, config)

    if result["success"]:
        tl.passed(LOG["oci_config_valid"].format(path=get_oci_config_path(host)))
    else:
        tl.failed(LOG["oci_config_invalid"].format(error="; ".join(result["errors"])))

    assert result["success"], ASSERT["oci_config_invalid"].format(
        error="; ".join(result["errors"])
    )


@pytest.mark.sanity
@pytest.mark.oci_image_ingest
@pytest.mark.order(102)
def test_oci_config_without_credentials(host):
    """Verify config without credentials is accepted by production validator."""
    tc = TC["oci_config_without_credentials"]
    tl = TestLogger(tc["title"], tc["id"])

    config = _load_live_config(host)
    result = run_production_validation(host, config)

    if result["success"]:
        tl.passed(LOG["oci_config_valid"].format(path=get_oci_config_path(host)))
    else:
        tl.failed(LOG["oci_config_invalid"].format(error="; ".join(result["errors"])))

    assert result["success"], ASSERT["oci_config_invalid"].format(
        error="; ".join(result["errors"])
    )


# =============================================================================
# NEGATIVE VALIDATION TESTS — invoke production run_validation()
# =============================================================================

@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(103)
def test_oci_unsupported_registry_type(host):
    """Verify unsupported registry type is rejected by the production validator.

    Passes configs with registry_type 'ecr' and 'dockerhub' through
    the production run_validation() and verifies the error message.
    """
    tc = TC["oci_unsupported_registry_type"]
    tl = TestLogger(tc["title"], tc["id"])

    config = _load_live_config(host)

    for bad_type in ("ecr", "dockerhub"):
        bad_config = copy.deepcopy(config)
        bad_config["registries"][0]["registry_type"] = bad_type
        result = run_production_validation(host, bad_config)
        assert not result["success"], (
            f"Production validator should reject registry_type '{bad_type}'"
        )
        joined = " ".join(result["errors"])
        assert "not yet supported" in joined, (
            f"Error should mention 'not yet supported', got: {joined}"
        )
        assert "harbor" in joined.lower(), (
            f"Error should list 'harbor' as supported, got: {joined}"
        )

    tl.passed(LOG["oci_registry_type_rejected"].format(value="ecr, dockerhub"))


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(104)
def test_oci_unsupported_operation(host):
    """Verify unsupported operation is rejected by the production validator."""
    tc = TC["oci_unsupported_operation"]
    tl = TestLogger(tc["title"], tc["id"])

    config = _load_live_config(host)
    bad_config = copy.deepcopy(config)
    bad_config["image_mappings"][0]["operation"] = "local_to_repo"
    result = run_production_validation(host, bad_config)

    assert not result["success"], (
        "Production validator should reject operation 'local_to_repo'"
    )
    joined = " ".join(result["errors"])
    assert "not yet supported" in joined, (
        f"Error should mention 'not yet supported', got: {joined}"
    )

    tl.passed(LOG["oci_operation_rejected"].format(value="local_to_repo"))


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(105)
def test_oci_credentials_in_config_rejected(host):
    """Verify credentials in config file are rejected by the production validator.

    Injects credential keys into the config and verifies the production
    validator rejects them without echoing the credential values.
    """
    tc = TC["oci_credentials_in_config_rejected"]
    tl = TestLogger(tc["title"], tc["id"])

    config = _load_live_config(host)
    bad_config = copy.deepcopy(config)
    bad_config["registries"][0]["registry_username"] = "testuser"
    bad_config["registries"][0]["registry_password"] = "s3cret_v@lue"
    result = run_production_validation(host, bad_config)

    assert not result["success"], (
        "Production validator should reject credential keys in config"
    )
    joined = " ".join(result["errors"])
    assert "oci_image_ingest_credentials.yml" in joined, (
        f"Error should redirect to credentials file, got: {joined}"
    )
    # Verify credential VALUES are never echoed
    assert "testuser" not in joined, "Credential value must not appear in error"
    assert "s3cret_v@lue" not in joined, "Credential value must not appear in error"

    tl.passed(LOG["oci_credentials_rejected"])


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(106)
def test_oci_missing_required_fields(host):
    """Verify missing required config fields are rejected by the production validator.

    Tests missing registries, missing image_mappings, missing image,
    and bad functional_group suffix — all through the production validator.
    """
    tc = TC["oci_missing_required_fields"]
    tl = TestLogger(tc["title"], tc["id"])

    config = _load_live_config(host)
    checks_passed = 0

    # Missing registries
    bad = copy.deepcopy(config)
    del bad["registries"]
    result = run_production_validation(host, bad)
    assert not result["success"], "Should reject missing registries"
    assert any("registries" in e.lower() for e in result["errors"])
    checks_passed += 1

    # Missing image_mappings
    bad = copy.deepcopy(config)
    del bad["image_mappings"]
    result = run_production_validation(host, bad)
    assert not result["success"], "Should reject missing image_mappings"
    assert any("image_mappings" in e.lower() for e in result["errors"])
    checks_passed += 1

    # Missing image field in mapping
    bad = copy.deepcopy(config)
    bad["image_mappings"][0].pop("image", None)
    result = run_production_validation(host, bad)
    assert not result["success"], "Should reject missing image field"
    checks_passed += 1

    # Bad functional_group suffix
    bad = copy.deepcopy(config)
    bad["image_mappings"][0]["functional_group"] = "slurm_node_rhel_10"
    result = run_production_validation(host, bad)
    assert not result["success"], "Should reject bad functional_group suffix"
    assert any("x86_64" in e or "aarch64" in e for e in result["errors"])
    checks_passed += 1

    tl.passed(f"All {checks_passed} missing-field rejection scenarios verified via production validator")


@pytest.mark.negative
@pytest.mark.oci_image_ingest
@pytest.mark.order(107)
def test_oci_unresolved_registry_reference(host):
    """Verify unresolved registry reference is caught by production semantic validation."""
    tc = TC["oci_unresolved_registry_reference"]
    tl = TestLogger(tc["title"], tc["id"])

    config = _load_live_config(host)
    bad_config = copy.deepcopy(config)
    bad_config["image_mappings"][0]["registry_name"] = "nonexistent-registry"
    result = run_production_validation(host, bad_config)

    assert not result["success"], (
        "Production validator should detect unresolved registry reference"
    )
    joined = " ".join(result["errors"])
    assert "nonexistent-registry" in joined, (
        f"Error should name the unresolved reference, got: {joined}"
    )
    assert "not defined" in joined.lower() or "is not defined" in joined.lower(), (
        f"Error should say reference is not defined, got: {joined}"
    )

    tl.passed("Unresolved registry reference detected by production semantic validator")
