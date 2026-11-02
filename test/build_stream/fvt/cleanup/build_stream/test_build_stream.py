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
Cleanup BuildStream — BuildStream removed by build_stream.yml --tags cleanup.

Containers (omnia_build_stream and omnia_postgres no longer running, then
removed), quadlet files, services, playbook-watcher (stopped, disabled, unit
file removed), runtime directories and caches, and the API port. Every checked
file, unit and directory is printed on its own line with a check mark.
The Postgres data follows cleanup.postgres_backup (false: data directory
and volumes deleted; true: preserved) and the
credential files follow cleanup.cleanup_credentials (true: deleted; false:
kept), as passed to the playbook from test_config.yml.
"""

import pytest

from library.functions import (
    TestLogger,
    check_buildstream_api_port_closed,
    check_buildstream_container_removed,
    check_buildstream_container_stopped,
    check_buildstream_directories_removed,
    check_buildstream_quadlet_files_removed,
    check_buildstream_runtime_caches_removed,
    check_buildstream_services_stopped,
    check_credentials_per_flag,
    check_playbook_watcher_service_disabled,
    check_playbook_watcher_service_file_removed,
    check_playbook_watcher_service_stopped,
    check_postgres_container_removed,
    check_postgres_container_stopped,
    check_postgres_data_per_backup,
    check_postgres_quadlet_files_removed,
    check_postgres_services_stopped,
    cleanup_settings,
    load_test_config,
    report_check,
)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import BUILDSTREAM_CREDENTIAL_FILES
from library.messages import TEST_ASSERT_MSGS as ASSERT


@pytest.mark.sanity
@pytest.mark.order(90201)
def test_buildstream_container_stopped(host):
    """Verify omnia_build_stream container is stopped."""
    tc = TC["buildstream_container_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_container_stopped(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="omnia_build_stream container", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90202)
def test_buildstream_container_removed(host):
    """Verify omnia_build_stream container is removed."""
    tc = TC["buildstream_container_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_container_removed(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="omnia_build_stream container", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90203)
def test_buildstream_quadlet_files_removed(host):
    """Verify omnia_build_stream quadlet files are removed."""
    tc = TC["buildstream_quadlet_files_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_quadlet_files_removed(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="omnia_build_stream quadlet files", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90204)
def test_buildstream_services_stopped(host):
    """Verify all omnia_build_stream systemd services are stopped."""
    tc = TC["buildstream_services_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_services_stopped(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="omnia_build_stream services", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90205)
def test_playbook_watcher_service_stopped(host):
    """Verify playbook-watcher service is stopped."""
    tc = TC["playbook_watcher_service_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_playbook_watcher_service_stopped(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="playbook-watcher.service", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90206)
def test_playbook_watcher_service_disabled(host):
    """Verify playbook-watcher service is disabled."""
    tc = TC["playbook_watcher_service_disabled"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_playbook_watcher_service_disabled(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="playbook-watcher.service (enabled at boot)", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90207)
def test_playbook_watcher_service_file_removed(host):
    """Verify playbook-watcher.service file is removed."""
    tc = TC["playbook_watcher_service_file_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_playbook_watcher_service_file_removed(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="playbook-watcher.service unit file", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90208)
def test_postgres_container_stopped(host):
    """Verify omnia_postgres container is stopped."""
    tc = TC["postgres_container_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_postgres_container_stopped(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="omnia_postgres container", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90209)
def test_postgres_container_removed(host):
    """Verify omnia_postgres container is removed."""
    tc = TC["postgres_container_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_postgres_container_removed(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="omnia_postgres container", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90210)
def test_postgres_quadlet_files_removed(host):
    """Verify omnia_postgres quadlet files are removed."""
    tc = TC["postgres_quadlet_files_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_postgres_quadlet_files_removed(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="omnia_postgres quadlet files", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90211)
def test_postgres_services_stopped(host):
    """Verify all omnia_postgres systemd services are stopped."""
    tc = TC["postgres_services_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_postgres_services_stopped(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="omnia_postgres services", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90212)
def test_buildstream_directories_removed(host):
    """Verify all BuildStream-generated runtime directories are removed."""
    tc = TC["buildstream_directories_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_directories_removed(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="BuildStream runtime directories", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90213)
def test_buildstream_runtime_caches_removed(host):
    """Verify runtime content is preserved and Python caches are removed."""
    tc = TC["buildstream_runtime_caches_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_runtime_caches_removed(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="BuildStream runtime caches", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90214)
def test_postgres_data_per_backup_flag(host):
    """Verify the Postgres data follows cleanup.postgres_backup."""
    tc = TC["postgres_data_per_backup_flag"]
    tl = TestLogger(tc["title"], tc["id"])
    flags = cleanup_settings(load_test_config())
    result = check_postgres_data_per_backup(host, flags["postgres_backup"])
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="Postgres data", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90215)
def test_buildstream_credentials_per_flag(host):
    """Verify build_stream_credentials.yml and its key follow cleanup.cleanup_credentials."""
    tc = TC["buildstream_credentials_per_flag"]
    tl = TestLogger(tc["title"], tc["id"])
    flags = cleanup_settings(load_test_config())
    result = check_credentials_per_flag(host, BUILDSTREAM_CREDENTIAL_FILES,
                                        flags["cleanup_credentials"])
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="build_stream credentials", error=result["error"],
    )


@pytest.mark.sanity
@pytest.mark.order(90217)
def test_buildstream_api_port_closed(host):
    """Verify the BuildStream API port is closed after cleanup."""
    tc = TC["buildstream_api_port_closed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_api_port_closed(host)
    report_check(tl, result)
    assert result["success"], ASSERT["cleanup_check_failed"].format(
        component="BuildStream API port", error=result["error"],
    )
