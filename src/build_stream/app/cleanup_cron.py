#!/usr/bin/env python3
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

"""Automated cleanup cron entry-point for FAILED Image Groups.

Run from inside the BuildStream container, scheduled every 24 hours
(configurable via ``CLEANUP_INTERVAL_HOURS``). For each ImageGroup in
status ``FAILED`` it:

1. Resolves the associated job_id (1:1 mapping).
2. Submits the Image Build Manager ``cleanup_images`` playbook through
   the shared playbook queue. That playbook removes S3/registry artifacts
   and prunes the global image dictionary for the image group.
3. Removes the per-Job NFS artifact directory.
4. Transitions the ImageGroup to ``CLEANING``. The result poller moves it
   to ``CLEANED`` and tombstones the Job after the playbook succeeds.
5. Records an audit event for the cleanup request.

Submission errors for one ImageGroup are logged and do NOT halt processing
of the remaining FAILED ImageGroups. Groups that remain ``FAILED`` are retried
on the next cycle; asynchronous playbook failures are recorded separately as
``CLEANUP_FAILED`` by the result poller.

Usage::

    python3 /opt/omnia/build_stream/cleanup_cron.py
"""

import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure local imports work whether invoked directly or via cron.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# pylint: disable=wrong-import-position
from api.logging_utils import log_secure_info  # noqa: E402
from core.image_group.value_objects import ImageGroupStatus  # noqa: E402
from core.localrepo.services import PlaybookQueueRequestService  # noqa: E402
from infra.repositories import (  # noqa: E402
    NfsPlaybookQueueRequestRepository,
)
from orchestrator.cleanup.use_cases.cleanup_job import (  # noqa: E402
    CleanupJobUseCase,
)


def _build_use_case(session) -> CleanupJobUseCase:
    """Wire the cleanup use case against SQL repositories for cron usage."""
    from infra.db.repositories import (  # pylint: disable=import-outside-toplevel
        SqlAuditEventRepository,
        SqlImageGroupRepository,
        SqlImageRepository,
        SqlJobRepository,
        SqlStageRepository,
    )
    from infra.id_generator import (  # pylint: disable=import-outside-toplevel
        UUIDv4Generator,
    )

    queue_service = PlaybookQueueRequestService(
        request_repo=NfsPlaybookQueueRequestRepository()
    )
    return CleanupJobUseCase(
        job_repo=SqlJobRepository(session=session),
        stage_repo=SqlStageRepository(session=session),
        audit_repo=SqlAuditEventRepository(session=session),
        image_group_repo=SqlImageGroupRepository(session=session),
        image_repo=SqlImageRepository(session=session),
        uuid_generator=UUIDv4Generator(),
        queue_service=queue_service,
    )


def main() -> int:
    """Run one pass of automated cleanup."""
    started_at = datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    correlation_id = f"cron-{uuid.uuid4()}"

    log_secure_info(
        "info",
        f"Auto-cleanup cron started: at={started_at}, "
        f"correlation_id={correlation_id}",
    )

    try:
        from infra.db.session import (  # pylint: disable=import-outside-toplevel
            SessionLocal,
        )
    except Exception as exc:  # pylint: disable=broad-except
        log_secure_info(
            "error",
            f"Auto-cleanup cron failed: cannot import SessionLocal: {exc}",
            exc_info=True,
        )
        return 2

    session = SessionLocal()
    try:
        from infra.db.repositories import (  # pylint: disable=import-outside-toplevel
            SqlImageGroupRepository,
        )

        image_group_repo = SqlImageGroupRepository(session=session)
        failed_groups = image_group_repo.list_by_status_all(
            ImageGroupStatus.FAILED
        )

        log_secure_info(
            "info",
            f"Auto-cleanup cron: found {len(failed_groups)} FAILED "
            f"ImageGroups",
        )

        if not failed_groups:
            return 0

        use_case = _build_use_case(session=session)
        cleaned = 0
        errors = 0

        for ig in failed_groups:
            job_id_str = str(ig.job_id)
            try:
                use_case.execute_auto(
                    job_id_str=job_id_str,
                    correlation_id=correlation_id,
                    reason="auto_cleanup_validation_failed",
                )
                cleaned += 1
            except Exception as exc:  # pylint: disable=broad-except
                errors += 1
                log_secure_info(
                    "error",
                    f"Auto-cleanup error for image_group_id={ig.id}, "
                    f"job_id={job_id_str}: {exc}",
                    job_id=job_id_str,
                    exc_info=True,
                )
                try:
                    session.rollback()
                except Exception:  # pylint: disable=broad-except
                    pass

        log_secure_info(
            "info",
            f"Auto-cleanup cron complete: total={len(failed_groups)}, "
            f"cleaned={cleaned}, errors={errors}",
        )
        return 0 if errors == 0 else 1

    except Exception as exc:  # pylint: disable=broad-except
        log_secure_info(
            "error",
            f"Auto-cleanup cron unexpected error: {exc}",
            exc_info=True,
        )
        return 2
    finally:
        try:
            session.close()
        except Exception:  # pylint: disable=broad-except
            pass


if __name__ == "__main__":
    sys.exit(main())
