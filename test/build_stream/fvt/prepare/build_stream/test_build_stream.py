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
Prepare BuildStream — Postgres, BuildStream API and playbook-watcher.

Validates what build_stream.yml --tags prepare deploys: enable flag,
containers, services, API health, database tables, venv, TLS
certificate, playbook queue and build_stream_status.yml.
"""

import pytest

from library.functions import (
    TestLogger,
    check_bsm_tls_certificate,
    check_build_stream_enabled,
    check_build_stream_health,
    check_buildstream_directories_present,
    check_nfs_queue_directory,
    check_omnia_venv,
    check_playbook_watcher,
    check_postgres_tables,
    check_prepare_containers,
    check_prepare_services,
    check_prepare_status_file,
    report_check,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    POSTGRES_DB_NAME,
)
from library.messages import TEST_ASSERT_MSGS as ASSERT


@pytest.mark.sanity
@pytest.mark.order(30101)
def test_build_stream_enabled(host):
    """Verify build_stream is enabled in build_stream_config.yml."""
    tc = TC["build_stream_enabled"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_build_stream_enabled(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["bsm_disabled"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(30102)
def test_prepare_containers(host):
    """Verify the BuildStream and Postgres containers run with their quadlets."""
    tc = TC["prepare_containers"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_prepare_containers(host)
    report_check(tl, result)
    assert result["success"], ASSERT["prepare_check_failed"].format(
        component="containers", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(30103)
def test_prepare_services(host):
    """Verify the Postgres, BuildStream and playbook-watcher services are active."""
    tc = TC["prepare_services"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_prepare_services(host)
    report_check(tl, result)
    assert result["success"], ASSERT["prepare_check_failed"].format(
        component="services", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(30104)
def test_build_stream_health(host):
    """Verify BSM API /health endpoint returns healthy."""
    tc = TC["build_stream_health"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_build_stream_health(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["bsm_health_fail"].format(url=result.get("url", "unknown"))
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(30105)
def test_postgres_tables(host):
    """Verify all expected tables exist in build_stream_db."""
    tc = TC["postgres_tables"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_postgres_tables(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["postgres_tables_missing"].format(
            db=POSTGRES_DB_NAME,
            missing=", ".join(result.get("missing", [])),
        )
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(30106)
def test_playbook_watcher_running(host):
    """Verify playbook watcher service is running (2.3)."""
    tc = TC["playbook_watcher_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_playbook_watcher(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["watcher_fail"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(30107)
def test_omnia_venv_exists(host):
    """Verify shared Python venv with ansible-playbook (2.3)."""
    tc = TC["omnia_venv_exists"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_omnia_venv(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["venv_missing"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(30108)
def test_bsm_tls_certificate_valid(host):
    """Verify BSM API TLS certificate is valid X.509 PEM (2.3)."""
    tc = TC["bsm_tls_certificate_valid"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_bsm_tls_certificate(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["tls_cert_invalid"]
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(30109)
def test_nfs_queue_directory_accessible(host):
    """Verify NFS queue directory accessible and writable (2.3)."""
    tc = TC["nfs_queue_directory_accessible"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_nfs_queue_directory(host)
    report_check(tl, result)
    assert result["success"], (
        ASSERT["nfs_queue_fail"].format(path=result.get("path", "unknown"))
        + (f"\nRoot cause: {result['error']}" if result.get("error") else "")
    )


@pytest.mark.sanity
@pytest.mark.order(30110)
def test_prepare_status_file(host):
    """Verify build_stream_status.yml reports prepared with every endpoint key."""
    tc = TC["prepare_status_file"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_prepare_status_file(host)
    report_check(tl, result)
    assert result["success"], ASSERT["prepare_check_failed"].format(
        component="build_stream_status.yml", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(30111)
def test_buildstream_directories_present(host):
    """Verify every runtime directory that prepare creates exists."""
    tc = TC["buildstream_directories_present"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_directories_present(host)
    report_check(tl, result)
    assert result["success"], ASSERT["prepare_check_failed"].format(
        component="runtime directories", error=result["error"],
    )
