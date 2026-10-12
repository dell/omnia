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

"""Automated cleanup entry-point.

Run inside the BuildStream container by the API's background
``AutoCleanupScheduler`` every ``retention.evaluation_interval_hours``
(default 24) from ``build_stream_config.yml``. It can also be run manually.

**Phase 1 — FAILED cleanup** (existing):
For each ImageGroup in status ``FAILED``:
1. Resolves the associated job_id (1:1 mapping).
2. Submits the Image Build Manager ``cleanup_images`` playbook through
   the shared playbook queue. That playbook removes S3/registry artifacts
   and prunes the global image dictionary for the image group.
3. Removes the per-Job NFS artifact directory.
4. Transitions the ImageGroup to ``CLEANING``. The result poller moves it
   to ``CLEANED`` and tombstones the Job after the playbook succeeds.
5. Records an audit event for the cleanup request.

**Phase 2 — Age-based retention** (ER-BSM-002 Story 4):
For each ImageGroup that meets ALL retention criteria:
  - age > retention.retention_age_days (default 90)
  - deploy_count = 0 (never deployed)
  - not tagged as protected
  - functional group has more than min_keep_count peers
The cron submits a cleanup request and emits RETENTION_DELETED audit events.
Per-ImageGroup failure isolation: one failure does NOT halt remaining evaluation.

Usage::

    python3 /opt/omnia/build_stream/cleanup_cron.py
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional

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
from orchestrator.cleanup.retention_config import (  # noqa: E402
    DEFAULT_MIN_KEEP_COUNT,
    DEFAULT_RETENTION_AGE_DAYS,
    RetentionConfig,
    load_retention_config,
)
from orchestrator.cleanup.use_cases.cleanup_job import (  # noqa: E402
    CleanupJobUseCase,
)

__all__ = [
    "DEFAULT_MIN_KEEP_COUNT",
    "DEFAULT_RETENTION_AGE_DAYS",
    "main",
]


def _load_retention_config() -> dict:
    """Load retention parameters from build_stream_config.yml.

    Returns a dict with keys: retention_age_days, min_keep_count.
    Falls back to defaults if the config file is missing or malformed.
    """
    config = load_retention_config()
    return {
        "retention_age_days": config.retention_age_days,
        "min_keep_count": config.min_keep_count,
    }


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


def _run_retention_evaluation(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    session, image_group_repo, use_case, correlation_id,
    retention_config: Optional[RetentionConfig] = None,
) -> tuple:
    """Run age-based retention evaluation (ER-BSM-002 Story 4).

    Args:
        session: SQLAlchemy DB session.
        image_group_repo: ImageGroup repository instance.
        use_case: CleanupJobUseCase (or None — will be built if needed).
        correlation_id: Tracing identifier.
        retention_config: Settings for this cycle; read from
            ``build_stream_config.yml`` when omitted.

    Returns:
        Tuple of (retention_deleted, retention_errors).
    """
    retention_config = retention_config or load_retention_config()
    retention_age_days = retention_config.retention_age_days
    min_keep_count = retention_config.min_keep_count

    log_secure_info(
        "info",
        f"Retention evaluation started: retention_age_days="
        f"{retention_age_days}, min_keep_count={min_keep_count}",
    )

    eligible = image_group_repo.list_eligible_for_retention(
        max_age_days=retention_age_days,
        min_keep_count=min_keep_count,
    )

    log_secure_info(
        "info",
        f"Retention evaluation: {len(eligible)} ImageGroups eligible "
        f"for deletion",
    )

    if not eligible:
        return 0, 0

    use_case = use_case or _build_use_case(session=session)
    from infra.db.repositories import (  # pylint: disable=import-outside-toplevel
        SqlAuditEventRepository,
    )
    from infra.id_generator import (  # pylint: disable=import-outside-toplevel
        UUIDv4Generator,
    )
    from core.jobs.entities import (  # pylint: disable=import-outside-toplevel
        AuditEvent,
    )
    audit_repo = SqlAuditEventRepository(session=session)
    uuid_gen = UUIDv4Generator()

    deleted = 0
    errors = 0
    for ig in eligible:
        job_id_str = str(ig.job_id)
        age_days = (datetime.now(timezone.utc) - ig.created_at).days
        try:
            use_case.execute_auto(
                job_id_str=job_id_str,
                correlation_id=correlation_id,
                reason="retention_age_exceeded",
            )
            audit_event = AuditEvent(
                event_id=str(uuid_gen.generate()),
                job_id=job_id_str,
                event_type="RETENTION_DELETED",
                details={
                    "image_group_id": str(ig.id),
                    "age_days": age_days,
                    "deploy_count": ig.deploy_count,
                    "reason": (
                        f"age={age_days}d > {retention_age_days}d, "
                        f"deploy_count=0, not_protected"
                    ),
                    "correlation_id": correlation_id,
                },
                created_at=datetime.now(timezone.utc),
            )
            audit_repo.save(audit_event)
            session.commit()
            deleted += 1
            log_secure_info(
                "info",
                f"RETENTION_DELETED: image_group_id={ig.id}, "
                f"age={age_days}d, deploy_count={ig.deploy_count}",
                job_id=job_id_str,
            )
        except Exception as exc:  # pylint: disable=broad-except
            errors += 1
            log_secure_info(
                "error",
                f"Retention cleanup error for "
                f"image_group_id={ig.id}, "
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
        f"Retention evaluation complete: eligible={len(eligible)}, "
        f"deleted={deleted}, errors={errors}",
    )
    return deleted, errors


def main(retention_config: Optional[RetentionConfig] = None) -> int:
    """Run one pass of automated cleanup.

    Args:
        retention_config: Settings for this pass. The scheduler passes the
            configuration it just reloaded; a manual run reads
            ``build_stream_config.yml`` directly.

    Returns:
        0 on success, 1 when some ImageGroups failed, 2 on fatal error.
    """
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

        use_case = None
        cleaned = 0
        errors = 0

        if not failed_groups:
            log_secure_info(
                "info",
                "Auto-cleanup cron: no FAILED ImageGroups found",
            )
        else:
            use_case = _build_use_case(session=session)
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
            f"Auto-cleanup cron (FAILED phase) complete: "
            f"total={len(failed_groups)}, cleaned={cleaned}, errors={errors}",
        )

        # Phase 2: Age-based retention evaluation (ER-BSM-002 Story 4)
        _ret_deleted, retention_errors = _run_retention_evaluation(
            session, image_group_repo, use_case, correlation_id,
            retention_config,
        )

        total_errors = errors + retention_errors
        return 0 if total_errors == 0 else 1

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
