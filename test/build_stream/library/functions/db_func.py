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

"""BuildStream database (build_stream_db in omnia_postgres) queries.

Queries run through ``podman exec`` with the container's own POSTGRES_USER,
so no database credential is read by the suite. Identifiers interpolated into
SQL are validated against strict patterns first.
"""

import re
from typing import Any, Dict, List, Optional, Pattern

from .execute_probe_func import run_cmd
from ..vars.execute_vars import (
    BSM_POSTGRES_CONTAINER,
    BSM_POSTGRES_DB,
    IMAGE_GROUP_ID_RE,
    SQL,
    TEST_SUMMARY_KEYS,
    UUID_RE,
)

_GROUP_FIELDS = ("id", "job_id", "status", "deploy_count", "last_deployed_at",
                 "catalog_version")
_STAGE_FIELDS = ("stage_name", "stage_state", "attempt", "error_code",
                 "error_summary", "log_file_path", "started_at")


def _require(pattern: Pattern[str], value: str, label: str) -> str:
    """Return ``value`` when it fully matches ``pattern`` (SQL injection guard)."""
    if not pattern.fullmatch(value or ""):
        raise ValueError(f"invalid {label}: {value!r}")
    return value


def query(host: Any, sql: str) -> Dict[str, Any]:
    """Run SQL in build_stream_db.

    Returns:
        Dict with keys: success, rows (list of column lists), error.
    """
    result = run_cmd(host, "podman_psql", container=BSM_POSTGRES_CONTAINER,
                     database=BSM_POSTGRES_DB, sql=sql)
    if result.rc != 0:
        return {"success": False, "rows": [],
                "error": (result.stderr or result.stdout).strip() or f"psql rc={result.rc}"}
    rows = [line.split("|") for line in result.stdout.splitlines() if line.strip()]
    return {"success": True, "rows": rows, "error": ""}


def db_now_epoch(host: Any) -> int:
    """Return the database clock as a UNIX epoch (avoids host clock skew)."""
    result = query(host, SQL["now_epoch"])
    if not result["success"] or not result["rows"]:
        raise RuntimeError(f"cannot read database time: {result['error']}")
    return int(result["rows"][0][0])


def job_since(host: Any, epoch: int, newest: bool = True) -> Optional[Dict[str, str]]:
    """Return the newest (or first) job created at or after ``epoch``."""
    sql = SQL["newest_job_since" if newest else "first_job_since"]
    result = query(host, sql.format(epoch=int(epoch)))
    if not result["success"] or not result["rows"]:
        return None
    job_id, state, created = result["rows"][0][:3]
    return {"job_id": job_id, "job_state": state, "created_at": created}


def get_job(host: Any, job_id: str) -> Optional[Dict[str, str]]:
    """Return the jobs row for ``job_id`` (or None)."""
    result = query(host, SQL["job"].format(job_id=_require(UUID_RE, job_id, "job_id")))
    if not result["success"] or not result["rows"]:
        return None
    row = result["rows"][0]
    return {"job_id": row[0], "job_state": row[1], "created_at": row[2], "updated_at": row[3]}


def get_stages(host: Any, job_id: str) -> Dict[str, Dict[str, str]]:
    """Return ``{stage_name: stage_row}`` for a job (empty on error)."""
    result = query(host, SQL["job_stages"].format(job_id=_require(UUID_RE, job_id, "job_id")))
    return {row[0]: dict(zip(_STAGE_FIELDS, row)) for row in result["rows"]
            if len(row) >= len(_STAGE_FIELDS)}


def stage_test_summary(host: Any, job_id: str, stage: str) -> Optional[Dict[str, int]]:
    """Return the ``result_detail.test_summary`` counts of a stage (None when absent)."""
    if not re.fullmatch(r"[a-z-]+", stage or ""):
        raise ValueError(f"invalid stage: {stage!r}")
    result = query(host, SQL["stage_test_summary"].format(
        job_id=_require(UUID_RE, job_id, "job_id"), stage=stage))
    if not result["success"] or not result["rows"]:
        return None
    row = [value.strip() for value in result["rows"][0]]
    if len(row) < len(TEST_SUMMARY_KEYS) or not all(value.isdigit() for value in row):
        return None
    return dict(zip(TEST_SUMMARY_KEYS, (int(value) for value in row)))


def _group(host: Any, sql: str) -> Optional[Dict[str, str]]:
    """Return the first image-group row of ``sql`` (or None)."""
    result = query(host, sql)
    if not result["success"] or not result["rows"]:
        return None
    return dict(zip(_GROUP_FIELDS, result["rows"][0]))


def image_group_for_job(host: Any, job_id: str) -> Optional[Dict[str, str]]:
    """Return the image group built by ``job_id`` (or None)."""
    return _group(host, SQL["image_group_by_job"].format(
        job_id=_require(UUID_RE, job_id, "job_id")))


def image_groups_for_job(host: Any, job_id: str) -> Dict[str, Any]:
    """Return every image group row owned by ``job_id``.

    Returns:
        Dict with keys: success, groups (list of row dicts), error.
    """
    result = query(host, SQL["image_groups_for_job"].format(
        job_id=_require(UUID_RE, job_id, "job_id")))
    groups = [dict(zip(_GROUP_FIELDS, row)) for row in result["rows"]
              if len(row) >= len(_GROUP_FIELDS)]
    return {"success": result["success"], "groups": groups, "error": result["error"]}


def job_client_id(host: Any, job_id: str) -> Optional[str]:
    """Return jobs.client_id of ``job_id`` ("" when unset, None when unreadable)."""
    result = query(host, SQL["job_client_id"].format(job_id=_require(UUID_RE, job_id, "job_id")))
    if not result["success"] or not result["rows"]:
        return None
    return result["rows"][0][0].strip()


def catalog_versions(host: Any, identifier: str) -> List[str]:
    """Return every catalog version recorded in image_groups for ``identifier``."""
    result = query(host, SQL["catalog_versions"].format(
        identifier=_require(IMAGE_GROUP_ID_RE, identifier, "catalog identifier")))
    return [row[0].strip() for row in result["rows"] if row and row[0].strip()]


def image_group(host: Any, image_group_id: str) -> Optional[Dict[str, str]]:
    """Return the image group ``image_group_id`` (or None)."""
    return _group(host, SQL["image_group_by_id"].format(
        image_group_id=_require(IMAGE_GROUP_ID_RE, image_group_id, "image_group_id")))


def image_group_count(host: Any) -> Dict[str, Any]:
    """Return how many image groups exist. Dict with keys: success, count, error."""
    result = query(host, SQL["image_group_count"])
    count = int(result["rows"][0][0]) if result["success"] and result["rows"] else 0
    return {"success": result["success"], "count": count, "error": result["error"]}


def newest_cleanable_image_group(host: Any) -> Optional[Dict[str, str]]:
    """Return the newest image group the cleanup API accepts (BUILT/PASSED/FAILED)."""
    return _group(host, SQL["newest_cleanable_image_group"])


def mark_image_group_failed(host: Any, image_group_id: str) -> Dict[str, Any]:
    """Set a BUILT/PASSED/FAILED image group to FAILED so the automated cleanup takes it.

    The new status is read back, so a group in any other state (for example
    DEPLOYING) is reported as an error instead of being changed.

    Returns:
        Dict with keys: success, previous (status before), error.
    """
    group = image_group(host, image_group_id)
    if group is None:
        return {"success": False, "previous": "",
                "error": f"image group {image_group_id} is not in build_stream_db"}
    previous = group["status"]
    result = query(host, SQL["mark_image_group_failed"].format(image_group_id=image_group_id))
    if not result["success"]:
        return {"success": False, "previous": previous, "error": result["error"]}
    current = (image_group(host, image_group_id) or {}).get("status", "")
    if current != "FAILED":
        return {"success": False, "previous": previous,
                "error": f"image group {image_group_id} is {current or 'missing'} and cannot "
                         "be marked FAILED (only BUILT, PASSED or FAILED groups can)"}
    return {"success": True, "previous": previous, "error": ""}


def image_roles(host: Any, image_group_id: str) -> List[str]:
    """Return the roles of the images recorded for an image group."""
    result = query(host, SQL["image_roles"].format(
        image_group_id=_require(IMAGE_GROUP_ID_RE, image_group_id, "image_group_id")))
    return [row[0].strip() for row in result["rows"] if row and row[0].strip()]


def job_tombstoned(host: Any, job_id: str) -> bool:
    """Return whether the jobs row of ``job_id`` is tombstoned."""
    result = query(host, SQL["jobs_tombstoned"].format(
        job_ids=f"'{_require(UUID_RE, job_id, 'job_id')}'"))
    return bool(result["rows"]) and len(result["rows"][0]) >= 2 and result["rows"][0][1] == "t"


def cleanup_audit_events(host: Any, job_id: str, since_epoch: int) -> List[str]:
    """Return the cleanup audit event types recorded for ``job_id`` since ``since_epoch``."""
    result = query(host, SQL["cleanup_audit_for_job"].format(
        job_id=_require(UUID_RE, job_id, "job_id"), epoch=int(since_epoch)))
    return sorted({row[0] for row in result["rows"] if row})


def image_count(host: Any, image_group_id: str) -> int:
    """Return how many images belong to an image group."""
    result = query(host, SQL["image_count"].format(
        image_group_id=_require(IMAGE_GROUP_ID_RE, image_group_id, "image_group_id")))
    return int(result["rows"][0][0]) if result["success"] and result["rows"] else 0
