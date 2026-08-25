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
BuildStream Domain Cleanup — Comprehensive Verification.

Validates that cleanup_build_stream.yml removed all artifacts:
  omnia_build_stream container stopped and removed
  omnia_build_stream quadlet files removed
  omnia_build_stream systemd services stopped
  playbook_watcher service stopped, disabled, file removed
  omnia_postgres container stopped and removed
  omnia_postgres quadlet files removed
  omnia_postgres systemd services stopped
  image_groups marked CLEANED
  Postgres volumes removed (no backup) or preserved (backup)
  build_stream cleanup directories removed
  build_stream credentials removed
  build_stream OAuth credentials removed
"""

import pytest

from library.functions import (
    TestLogger,
    check_buildstream_container_stopped,
    check_buildstream_container_removed,
    check_buildstream_quadlet_files_removed,
    check_buildstream_services_stopped,
    check_playbook_watcher_service_stopped,
    check_playbook_watcher_service_disabled,
    check_playbook_watcher_service_file_removed,
    check_postgres_container_stopped,
    check_postgres_container_removed,
    check_postgres_quadlet_files_removed,
    check_postgres_services_stopped,
    check_image_groups_marked_cleaned,
    check_postgres_volumes_removed,
    check_postgres_volumes_preserved,
    check_buildstream_directories_removed,
    check_buildstream_credentials_removed,
    check_buildstream_oauth_credentials_removed,
)
from library.vars import TEST_CASES as TC
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)


# =====================================================================
# Container Cleanup
# =====================================================================

@pytest.mark.sanity
@pytest.mark.order(9)
def test_buildstream_container_stopped(host):
    """Verify omnia_build_stream container is stopped."""
    tc = TC["buildstream_container_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_container_stopped(host)

    if result["success"]:
        tl.passed(
            LOG["container_not_found"].format(
                container=result["container"],
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["container_still_exists"].format(
                container=result["container"],
                status=result.get("status", ""),
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["container_still_exists"].format(
        container=result["container"],
    )


@pytest.mark.sanity
@pytest.mark.order(10)
def test_buildstream_container_removed(host):
    """Verify omnia_build_stream container is removed."""
    tc = TC["buildstream_container_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_container_removed(host)

    if result["success"]:
        tl.passed(
            LOG["container_not_found"].format(
                container=result["container"],
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["container_still_exists"].format(
                container=result["container"],
                status=result.get("status", ""),
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["container_still_exists"].format(
        container=result["container"],
    )


@pytest.mark.sanity
@pytest.mark.order(11)
def test_buildstream_quadlet_files_removed(host):
    """Verify omnia_build_stream quadlet files are removed."""
    tc = TC["buildstream_quadlet_files_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_quadlet_files_removed(host)

    if result["success"]:
        tl.passed(
            LOG["quadlet_files_removed"].format(
                pattern="omnia_build_stream",
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["quadlet_files_still_exist"].format(
                files=result.get("error", ""),
            ),
        )

    assert result["success"], result.get(
        "error", "Quadlet files not removed"
    )


@pytest.mark.sanity
@pytest.mark.order(12)
def test_buildstream_services_stopped(host):
    """Verify all omnia_build_stream systemd services are stopped."""
    tc = TC["buildstream_services_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_services_stopped(host)

    if result["success"]:
        tl.passed(result["details"])
    else:
        tl.failed(result.get("error", ""))

    assert result["success"], ASSERT["service_still_active"].format(
        service="omnia_build_stream",
    )


# =====================================================================
# Playbook Watcher Cleanup
# =====================================================================

@pytest.mark.sanity
@pytest.mark.order(13)
def test_playbook_watcher_service_stopped(host):
    """Verify playbook_watcher service is stopped."""
    tc = TC["playbook_watcher_service_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_playbook_watcher_service_stopped(host)

    if result["success"]:
        tl.passed(
            LOG["service_inactive"].format(
                service="playbook_watcher.service",
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["service_still_active"].format(
                service="playbook_watcher.service",
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["service_still_active"].format(
        service="playbook_watcher.service",
    )


@pytest.mark.sanity
@pytest.mark.order(14)
def test_playbook_watcher_service_disabled(host):
    """Verify playbook_watcher service is disabled."""
    tc = TC["playbook_watcher_service_disabled"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_playbook_watcher_service_disabled(host)

    if result["success"]:
        tl.passed(
            LOG["service_disabled"].format(
                service="playbook_watcher.service",
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["service_still_enabled"].format(
                service="playbook_watcher.service",
            ),
            result.get("error", ""),
        )

    assert result["success"], result.get(
        "error", "Service still enabled"
    )


@pytest.mark.sanity
@pytest.mark.order(15)
def test_playbook_watcher_service_file_removed(host):
    """Verify playbook_watcher.service file is removed."""
    tc = TC["playbook_watcher_service_file_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_playbook_watcher_service_file_removed(host)

    if result["success"]:
        tl.passed(
            LOG["service_file_removed"].format(path=result["path"]),
            result["details"],
        )
    else:
        tl.failed(
            LOG["service_file_still_exists"].format(
                path=result["path"],
            ),
            result.get("error", ""),
        )

    assert result["success"], result.get(
        "error", "Service file not removed"
    )


# =====================================================================
# Postgres Cleanup
# =====================================================================

@pytest.mark.sanity
@pytest.mark.order(16)
def test_postgres_container_stopped(host):
    """Verify omnia_postgres container is stopped."""
    tc = TC["postgres_container_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_postgres_container_stopped(host)

    if result["success"]:
        tl.passed(
            LOG["container_not_found"].format(
                container=result["container"],
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["container_still_exists"].format(
                container=result["container"],
                status=result.get("status", ""),
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["container_still_exists"].format(
        container=result["container"],
    )


@pytest.mark.sanity
@pytest.mark.order(17)
def test_postgres_container_removed(host):
    """Verify omnia_postgres container is removed."""
    tc = TC["postgres_container_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_postgres_container_removed(host)

    if result["success"]:
        tl.passed(
            LOG["container_not_found"].format(
                container=result["container"],
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["container_still_exists"].format(
                container=result["container"],
                status=result.get("status", ""),
            ),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["container_still_exists"].format(
        container=result["container"],
    )


@pytest.mark.sanity
@pytest.mark.order(18)
def test_postgres_quadlet_files_removed(host):
    """Verify omnia_postgres quadlet files are removed."""
    tc = TC["postgres_quadlet_files_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_postgres_quadlet_files_removed(host)

    if result["success"]:
        tl.passed(
            LOG["quadlet_files_removed"].format(
                pattern="omnia_postgres",
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["quadlet_files_still_exist"].format(
                files=result.get("error", ""),
            ),
        )

    assert result["success"], result.get(
        "error", "Quadlet files not removed"
    )


@pytest.mark.sanity
@pytest.mark.order(19)
def test_postgres_services_stopped(host):
    """Verify all omnia_postgres systemd services are stopped."""
    tc = TC["postgres_services_stopped"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_postgres_services_stopped(host)

    if result["success"]:
        tl.passed(result["details"])
    else:
        tl.failed(result.get("error", ""))

    assert result["success"], ASSERT["service_still_active"].format(
        service="omnia_postgres",
    )


@pytest.mark.sanity
@pytest.mark.order(20)
def test_image_groups_marked_cleaned(host):
    """Verify all image_groups are updated to CLEANED status."""
    tc = TC["image_groups_marked_cleaned"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_image_groups_marked_cleaned(host)

    if result.get("skipped"):
        tl.skipped(LOG["image_groups_not_checked"])
        pytest.skip(LOG["image_groups_not_checked"])

    if result["success"]:
        tl.passed(LOG["image_groups_cleaned"], result["details"])
    else:
        tl.failed(result.get("error", ""))

    assert result["success"], result.get(
        "error", "image_groups not marked CLEANED"
    )


@pytest.mark.sanity
@pytest.mark.order(21)
def test_postgres_volumes_removed_no_backup(host):
    """Verify Postgres volumes removed when postgres_backup=false."""
    tc = TC["postgres_volumes_removed_no_backup"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_postgres_volumes_removed(host)

    if result["success"]:
        tl.passed(
            LOG["volumes_removed"].format(
                container="omnia_postgres",
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["volumes_still_exist"].format(
                volumes=", ".join(result.get("volumes", [])),
            ),
            result.get("error", ""),
        )

    assert result["success"], result.get(
        "error", "Postgres volumes not removed"
    )


@pytest.mark.sanity
@pytest.mark.order(22)
def test_postgres_volumes_preserved_with_backup(host):
    """Verify Postgres volumes preserved when postgres_backup=true."""
    tc = TC["postgres_volumes_preserved_with_backup"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_postgres_volumes_preserved(host)

    if result["success"]:
        tl.passed(LOG["volumes_preserved_ok"], result["details"])
    else:
        tl.failed(result.get("error", ""))

    assert result["success"], result.get(
        "error", "Postgres volumes not preserved"
    )


# =====================================================================
# Directory Cleanup
# =====================================================================

@pytest.mark.sanity
@pytest.mark.order(23)
def test_buildstream_directories_removed(host):
    """Verify build_stream cleanup directories are removed."""
    tc = TC["buildstream_directories_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_directories_removed(host)

    if result["success"]:
        tl.passed(
            LOG["dirs_removed"].format(
                count=len(result["removed"]),
                total=len(result["removed"]),
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["dirs_still_exist"].format(
                dirs=", ".join(result["still_exist"]),
            ),
            result["details"],
        )

    assert result["success"], ASSERT["dirs_still_exist"].format(
        dirs=", ".join(result.get("still_exist", [])),
    )


# =====================================================================
# Credential Cleanup
# =====================================================================

@pytest.mark.sanity
@pytest.mark.order(24)
def test_buildstream_credentials_removed(host):
    """Verify build_stream_credentials.yml and vault key removed."""
    tc = TC["buildstream_credentials_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_credentials_removed(host)

    if result["success"]:
        tl.passed(
            LOG["creds_removed"].format(
                count=len(result["removed"]),
                total=len(result["removed"]),
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["creds_still_exist"].format(
                files=", ".join(result["still_exist"]),
            ),
            result["details"],
        )

    assert result["success"], ASSERT["creds_still_exist"].format(
        files=", ".join(result.get("still_exist", [])),
    )


@pytest.mark.sanity
@pytest.mark.order(25)
def test_buildstream_oauth_credentials_removed(host):
    """Verify build_stream_oauth_credentials.yml and key removed."""
    tc = TC["buildstream_oauth_credentials_removed"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_buildstream_oauth_credentials_removed(host)

    if result["success"]:
        tl.passed(
            LOG["creds_removed"].format(
                count=len(result["removed"]),
                total=len(result["removed"]),
            ),
            result["details"],
        )
    else:
        tl.failed(
            LOG["creds_still_exist"].format(
                files=", ".join(result["still_exist"]),
            ),
            result["details"],
        )

    assert result["success"], ASSERT["creds_still_exist"].format(
        files=", ".join(result.get("still_exist", [])),
    )
