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
"""Live negative security tests for the installed BuildStream API."""

import uuid

import pytest

from library.functions import (
    TestLogger,
    artifact_path_absent,
    bsm_request,
    check_file_permissions,
    create_disposable_job,
    forbidden_upload_absent,
    get_bsm_context,
    get_bsm_job_details,
    get_scoped_token,
    load_test_config,
    secret_absent_from_bsm_logs,
    upload_inline_file,
    upload_oversized_file,
)
from library.vars import TEST_CASES as TC


POSTGRES_QUADLET_PATH = "/etc/containers/systemd/omnia_postgres.container"
BUILD_STREAM_QUADLET_PATH = (
    "/etc/containers/systemd/omnia_build_stream.container"
)


def _case(name):
    details = TC[name]
    return TestLogger(details["title"], details["id"])


def _mutation_enabled(config, logger):
    if not config.get("nft_allow_security_mutation", False):
        logger.skipped(
            "Set nft_allow_security_mutation: true to create one disposable test job"
        )
        pytest.skip("nft_allow_security_mutation is false")


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(10)
def test_protected_endpoints_reject_invalid_tokens(host):
    """Missing, malformed, and signature-tampered tokens must all return 401."""
    logger = _case("protected_endpoints_reject_invalid_tokens")
    context = get_bsm_context(host)
    assert context["success"], context["error"]
    unknown_job = str(uuid.uuid4())
    tokens = [None, "not-a-jwt", f"{context['token']}tampered"]
    statuses = []
    for token in tokens:
        response = bsm_request(host, "GET", f"/jobs/{unknown_job}", token=token)
        assert response["success"], response["error"]
        statuses.append(response["status"])
    assert statuses == [401, 401, 401], f"Unexpected authentication statuses: {statuses}"
    logger.passed("Missing, malformed, and tampered bearer tokens returned HTTP 401")


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(11)
def test_scope_authorization_enforced(host):
    """A catalog-read token must not invoke a job-write restart operation."""
    logger = _case("scope_authorization_enforced")
    scoped = get_scoped_token(host, "catalog:read")
    assert scoped["success"], scoped["error"]
    response = bsm_request(
        host, "POST", f"/jobs/{uuid.uuid4()}/stages/restart",
        token=scoped["token"],
    )
    assert response["success"], response["error"]
    assert response["status"] == 403, (
        f"Read-only token returned HTTP {response['status']}; expected 403"
    )
    logger.passed("Read-only OAuth token was denied access to a job-write endpoint")


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(12)
def test_upload_path_and_filename_protection(host, nft_state):
    """Traversal filename must fail before creating any artifact or stage change."""
    logger = _case("upload_path_and_filename_protection")
    config = load_test_config()
    _mutation_enabled(config, logger)
    context = get_bsm_context(host)
    assert context["success"], context["error"]
    created = create_disposable_job(host)
    assert created["status"] == 201 and created["job_id"], created.get("body", "")
    job_id = created["job_id"]
    nft_state["security_job_id"] = job_id
    before = get_bsm_job_details(host, job_id)
    assert before["success"], before["error"]

    basename = f"bsm_nft_escape_{uuid.uuid4().hex}.yml"
    response = upload_inline_file(
        host, job_id, f"../../{basename}", "test: value", context["token"],
    )
    assert response["status"] == 400, response.get("body", "")
    assert forbidden_upload_absent(host, basename), "Traversal upload created a file"
    after = get_bsm_job_details(host, job_id)
    assert after["success"], after["error"]
    assert after["job"].get("stages") == before["job"].get("stages"), (
        "Rejected upload changed stage state"
    )
    logger.passed("Traversal filename was rejected without filesystem or stage mutation")


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(13)
def test_oversized_upload_rejected_without_partial_state(host, nft_state):
    """An upload above the configured 5 MiB limit must leave no partial file."""
    logger = _case("oversized_upload_rejected_without_partial_state")
    config = load_test_config()
    _mutation_enabled(config, logger)
    context = get_bsm_context(host)
    assert context["success"], context["error"]
    job_id = nft_state.get("security_job_id", "")
    if not job_id:
        created = create_disposable_job(host)
        assert created["status"] == 201 and created["job_id"], created.get("body", "")
        job_id = created["job_id"]
        nft_state["security_job_id"] = job_id
    before = get_bsm_job_details(host, job_id)
    assert before["success"], before["error"]

    response = upload_oversized_file(host, job_id, context["token"])
    assert response["status"] == 400, response.get("body", response.get("error", ""))
    assert artifact_path_absent(host, job_id, "build_stream_config.yml")
    after = get_bsm_job_details(host, job_id)
    assert after["success"], after["error"]
    assert after["job"].get("stages") == before["job"].get("stages"), (
        "Rejected oversized upload changed stage state"
    )
    logger.passed("Oversized upload was rejected without partial artifact or stage mutation")


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(14)
def test_secret_redaction_in_logs_and_responses(host):
    """Invalid client-secret canary must not be echoed or written to BSM logs."""
    logger = _case("secret_redaction_in_logs_and_responses")
    context = get_bsm_context(host)
    assert context["success"], context["error"]
    canary = f"bld_s_BSM_NFT_SECRET_{uuid.uuid4().hex}"
    response = bsm_request(
        host, "POST", "/auth/token", token=None,
        form_body={
            "grant_type": "client_credentials",
            "client_id": context["client_id"],
            "client_secret": canary,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response["status"] in {400, 401}, response.get("body", "")
    assert canary not in response.get("body", ""), "Client secret was echoed in response"
    assert secret_absent_from_bsm_logs(host, canary), "Client secret was written to BSM logs"
    logger.passed("Invalid OAuth secret was absent from API response and container logs")


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(15)
def test_postgres_quadlet_permissions(host):
    """omnia_postgres quadlet must be 0600 root:root (embeds DB superuser password)."""
    logger = _case("postgres_quadlet_permissions")
    result = check_file_permissions(
        host, POSTGRES_QUADLET_PATH,
        expected_mode="0600",
        expected_owner="root",
        expected_group="root",
    )
    if result["success"]:
        logger.passed(result["details"])
    else:
        logger.failed(result["details"])
    assert result["success"], result["details"]


@pytest.mark.nft
@pytest.mark.security
@pytest.mark.order(16)
def test_build_stream_quadlet_permissions(host):
    """omnia_build_stream quadlet must be 0600 root:root (holds Postgres/MinIO creds)."""
    logger = _case("build_stream_quadlet_permissions")
    result = check_file_permissions(
        host, BUILD_STREAM_QUADLET_PATH,
        expected_mode="0600",
        expected_owner="root",
        expected_group="root",
    )
    if result["success"]:
        logger.passed(result["details"])
    else:
        logger.failed(result["details"])
    assert result["success"], result["details"]



