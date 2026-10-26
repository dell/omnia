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
Prepare Base — Base Domain Readiness Verification.

Validates that ./omnia.sh --prepare-base left the BuildStream prerequisites
running, following each producing role's readiness contract:
  repo_manager         Pulp quadlet present, pulp.service active, container
                       running
  image_build_manager  MinIO and registry containers running, services
                       active, ports 9000/9001/5000 listening
  orchestrator         all 14 OpenCHAMI units (openchami.target and every
                       service, one-shot units included) and the cert renewal
                       timer active; the 9 long-running containers running
                       (healthcheck honoured); data and HAProxy cert volumes
                       present; OpenLDAP quadlet, service and container when
                       orchestrator_state.yml sets openldap_support
Every checked item is listed with a check or cross mark.
"""

import pytest

from library.functions import (
    TestLogger,
    failure_summary,
    verify_image_build_manager_ready,
    verify_orchestrator_ready,
    verify_repo_manager_ready,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT, TEST_LOG_MSGS as LOG
from library.vars import TEST_CASES as TC


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.prepare_base
@pytest.mark.sanity
@pytest.mark.order(1101)
def test_repo_manager_ready(host):
    """Verify repo_manager prepare left Pulp deployed and running."""
    tc = TC["repo_manager_ready"]
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_repo_manager_ready(host)

    if result["success"]:
        tl.passed_fields(LOG["ready_ok"].format(domain="repo_manager"), result["fields"])
    else:
        tl.failed_fields(LOG["ready_failed"].format(
            domain="repo_manager", count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["ready_failed"].format(
        domain="repo_manager", failures=failure_summary(result))


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.prepare_base
@pytest.mark.sanity
@pytest.mark.order(1102)
def test_image_build_manager_ready(host):
    """Verify image_build_manager prepare left MinIO and the registry serving."""
    tc = TC["image_build_manager_ready"]
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_image_build_manager_ready(host)

    if result["success"]:
        tl.passed_fields(LOG["ready_ok"].format(domain="image_build_manager"), result["fields"])
    else:
        tl.failed_fields(LOG["ready_failed"].format(
            domain="image_build_manager", count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["ready_failed"].format(
        domain="image_build_manager", failures=failure_summary(result))


@pytest.mark.e2e
@pytest.mark.br_86010
@pytest.mark.prepare_base
@pytest.mark.sanity
@pytest.mark.order(1103)
def test_orchestrator_ready(host):
    """Verify orchestrator prepare left every OpenCHAMI and OpenLDAP component up."""
    tc = TC["orchestrator_ready"]
    tl = TestLogger(tc["title"], tc["id"])
    result = verify_orchestrator_ready(host)

    if result["success"]:
        tl.passed_fields(LOG["ready_ok"].format(domain="orchestrator"), result["fields"])
    else:
        tl.failed_fields(LOG["ready_failed"].format(
            domain="orchestrator", count=len(result["failures"])), result["fields"])
    assert result["success"], ASSERT["ready_failed"].format(
        domain="orchestrator", failures=failure_summary(result))
