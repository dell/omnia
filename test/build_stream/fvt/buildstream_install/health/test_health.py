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
Build Stream Health — Service Health Verification.

Validates that build_stream infrastructure is healthy:
  build_stream enabled in config
  BSM API /health endpoint returns healthy
  Postgres database tables exist
  GitLab server and runner running
  Shared Python venv with ansible-playbook (2.3)
  BSM TLS certificate valid (2.3)
  NFS queue directory accessible (2.3)
  Playbook watcher service running (2.3)
"""

import pytest

from library.functions import (
    TestLogger,
    check_build_stream_enabled,
    check_build_stream_health,
    check_postgres_tables,
    check_gitlab_url_accessible,
    check_gitlab_runner_container,
    check_omnia_venv,
    check_bsm_tls_certificate,
    check_nfs_queue_directory,
    check_playbook_watcher,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import POSTGRES_DB_NAME
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


@pytest.mark.sanity
@pytest.mark.order(1)
def test_build_stream_enabled(host):
    """Verify build_stream is enabled in build_stream_config.yml."""
    tc = TC["build_stream_enabled"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_build_stream_enabled(host)

    if result["success"]:
        tl.passed(LOG["bsm_enabled"], result["details"])
    else:
        tl.failed(LOG["bsm_disabled"])

    assert result["success"], (
        ASSERT["bsm_disabled"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(2)
def test_build_stream_health(host):
    """Verify BSM API /health endpoint returns healthy."""
    tc = TC["build_stream_health"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_build_stream_health(host)

    if result["success"]:
        tl.passed(LOG["bsm_health_ok"].format(url=result["url"]))
    else:
        tl.failed(LOG["bsm_health_fail"].format(
            url=result.get("url", "unknown"),
        ))

    assert result["success"], (
        ASSERT["bsm_health_fail"].format(url=result.get("url", "unknown"))
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(3)
def test_postgres_tables(host):
    """Verify all expected tables exist in build_stream_db."""
    tc = TC["postgres_tables"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_postgres_tables(host)

    if result["success"]:
        tl.passed(LOG["postgres_tables_ok"].format(
            count=len(result["found"]), db=POSTGRES_DB_NAME,
        ))
    else:
        tl.failed(LOG["postgres_tables_missing"].format(
            db=POSTGRES_DB_NAME,
            missing=", ".join(result["missing"]),
        ))

    assert result["success"], (
        ASSERT["postgres_tables_missing"].format(
            db=POSTGRES_DB_NAME,
            missing=", ".join(result.get("missing", [])),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(4)
def test_gitlab_server_running(host):
    """Verify GitLab server is running and accessible."""
    tc = TC["gitlab_server_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_url_accessible(host)

    if result["success"]:
        tl.passed(LOG["url_accessible"].format(
            url=result["url"], code=result["http_code"],
        ))
    else:
        tl.failed(LOG["url_not_accessible"].format(
            url=result.get("url", "unknown"),
        ))

    assert result["success"], (
        ASSERT["url_not_accessible"].format(
            url=result.get("url", "unknown"),
            code=result.get("http_code", 0),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(5)
def test_gitlab_runner_running(host):
    """Verify GitLab runner container is running."""
    tc = TC["gitlab_runner_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_gitlab_runner_container(host)

    if result["success"]:
        tl.passed(LOG["runner_container_ok"], result["details"])
    else:
        tl.failed(LOG["runner_container_missing"])

    assert result["success"], (
        ASSERT["runner_container_missing"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(6)
def test_omnia_venv_exists(host):
    """Verify shared Python venv with ansible-playbook (2.3)."""
    tc = TC["omnia_venv_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_omnia_venv(host)

    if result["success"]:
        tl.passed(LOG["venv_ok"], result["details"])
    else:
        tl.failed(LOG["venv_missing"])

    assert result["success"], (
        ASSERT["venv_missing"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(7)
def test_bsm_tls_certificate_valid(host):
    """Verify BSM API TLS certificate is valid X.509 PEM (2.3)."""
    tc = TC["bsm_tls_certificate_valid"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_bsm_tls_certificate(host)

    if result["success"]:
        tl.passed(LOG["tls_cert_ok"], result["details"])
    else:
        tl.failed(LOG["tls_cert_invalid"])

    assert result["success"], (
        ASSERT["tls_cert_invalid"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(8)
def test_nfs_queue_directory_accessible(host):
    """Verify NFS queue directory accessible and writable (2.3)."""
    tc = TC["nfs_queue_directory_accessible"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_nfs_queue_directory(host)

    if result["success"]:
        tl.passed(LOG["nfs_queue_ok"], result["details"])
    else:
        tl.failed(LOG["nfs_queue_fail"])

    assert result["success"], (
        ASSERT["nfs_queue_fail"].format(path=result.get("path", "unknown"))
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(9)
def test_playbook_watcher_running(host):
    """Verify playbook watcher service is running (2.3)."""
    tc = TC["playbook_watcher_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_playbook_watcher(host)

    if result["success"]:
        tl.passed(LOG["watcher_ok"], result["details"])
    else:
        tl.failed(LOG["watcher_fail"])

    assert result["success"], (
        ASSERT["watcher_fail"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )
