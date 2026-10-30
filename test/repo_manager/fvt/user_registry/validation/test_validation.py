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
Repo Manager User Registry — Validation Verification.

Validates that user registry configuration is correct:
  Registries section exists in repo_manager_config.yml
  Registry entries have valid structure
  Registry base_url values are valid HTTP(S) origins
  Configured registries are reachable
  TLS certificate paths exist on disk
  Client cert and key are configured together
  Registry auth type is valid (none or basic)
  Credentials are configured for basic auth registries
"""

import pytest

from library.functions import (
    TestLogger,
    check_user_registry_section_exists,
    check_user_registry_structure,
    check_user_registry_base_url_valid,
    check_user_registry_reachability,
    check_user_registry_tls_cert_paths,
    check_user_registry_tls_pair_consistent,
    check_user_registry_auth_type,
    check_user_registry_credentials,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(1)
def test_user_registry_section_exists(host):
    """Verify registries section exists in repo_manager_config.yml."""
    tc = TC["user_registry_section_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_user_registry_section_exists(host)

    if result["success"]:
        tl.passed(LOG["user_registry_section_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_section_missing"], result["details"])

    assert result["success"], ASSERT["user_registry_section_must_exist"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(2)
def test_user_registry_structure_valid(host):
    """Verify registry entries have valid structure."""
    tc = TC["user_registry_structure_valid"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_user_registry_structure(host)

    if result.get("skipped"):
        tl.skipped_fields(
            "No registries configured",
            {
                "Registries": 0,
                "Configuration": "user_registry",
            }
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_structure_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_structure_invalid"], result["details"])

    assert result["success"], ASSERT["user_registry_structure_must_be_valid"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(3)
def test_user_registry_base_url_valid(host):
    """Verify registry base_url values are valid HTTP(S) origins."""
    tc = TC["user_registry_base_url_valid"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_user_registry_base_url_valid(host)

    if result.get("skipped"):
        tl.skipped_fields(
            "No registries configured",
            {
                "Registries": 0,
                "Configuration": "user_registry",
            }
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_base_url_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_base_url_invalid"], result["details"])

    assert result["success"], ASSERT["user_registry_base_url_must_be_valid"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(4)
def test_user_registry_reachable(host):
    """Verify configured registries are reachable."""
    tc = TC["user_registry_reachable"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_user_registry_reachability(host)

    if result.get("skipped"):
        tl.skipped_fields(
            "No registries configured",
            {
                "Registries": 0,
                "Configuration": "user_registry",
            }
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_reachable_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_unreachable"], result["details"])

    assert result["success"], ASSERT["user_registry_must_be_reachable"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(5)
def test_user_registry_tls_cert_paths_valid(host):
    """Verify TLS certificate paths exist on disk."""
    tc = TC["user_registry_tls_cert_paths_valid"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_user_registry_tls_cert_paths(host)

    if result.get("skipped"):
        tl.skipped_fields(
            "No registries configured",
            {
                "Registries": 0,
                "Configuration": "user_registry",
            }
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_tls_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_tls_invalid"], result["details"])

    assert result["success"], ASSERT["user_registry_tls_must_be_valid"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(6)
def test_user_registry_tls_pair_consistent(host):
    """Verify client cert and key are configured together."""
    tc = TC["user_registry_tls_pair_consistent"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_user_registry_tls_pair_consistent(host)

    if result.get("skipped"):
        tl.skipped_fields(
            "No registries configured",
            {
                "Registries": 0,
                "Configuration": "user_registry",
            }
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_tls_pair_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_tls_pair_invalid"], result["details"])

    assert result["success"], ASSERT["user_registry_tls_pair_must_be_consistent"]


@pytest.mark.sanity
@pytest.mark.positive
@pytest.mark.order(7)
def test_user_registry_auth_type_valid(host):
    """Verify registry auth type is valid (none or basic)."""
    tc = TC["user_registry_auth_type_valid"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_user_registry_auth_type(host)

    if result.get("skipped"):
        tl.skipped_fields(
            "No registries configured",
            {
                "Registries": 0,
                "Configuration": "user_registry",
            }
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_auth_type_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_auth_type_invalid"], result["details"])

    assert result["success"], ASSERT["user_registry_auth_type_must_be_valid"]


@pytest.mark.functional
@pytest.mark.positive
@pytest.mark.order(8)
def test_user_registry_credentials_present(host):
    """Verify credentials are configured for basic auth registries."""
    tc = TC["user_registry_credentials_present"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_user_registry_credentials(host)

    if result.get("skipped"):
        tl.skipped_fields(
            "No registries configured",
            {
                "Registries": 0,
                "Configuration": "user_registry",
            }
        )
        pytest.skip("No registries configured")

    if result["success"]:
        tl.passed(LOG["user_registry_credentials_ok"], result["details"])
    else:
        tl.failed(LOG["user_registry_credentials_missing"], result["details"])

    assert result["success"], ASSERT["user_registry_credentials_must_exist"]
