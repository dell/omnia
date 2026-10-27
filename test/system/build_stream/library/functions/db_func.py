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

from typing import Any, Dict, List, Optional, Pattern, Sequence

from .probe_func import run_cmd
from ..vars.common_vars import (
    BSM_POSTGRES_CONTAINER,
    BSM_POSTGRES_DB,
    IMAGE_GROUP_ID_RE,
    SQL,
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


def list_tables(host: Any) -> Dict[str, Any]:
    """Return public tables. Dict with keys: success, tables, error."""
    result = query(host, SQL["tables"])
    return {"success": result["success"], "tables": [r[0] for r in result["rows"]],
            "error": result["error"]}


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


def catalog_versions(host: Any, identifier: str) -> List[str]:
    """Return every catalog version recorded in image_groups for ``identifier``."""
    result = query(host, SQL["catalog_versions"].format(
        identifier=_require(IMAGE_GROUP_ID_RE, identifier, "catalog identifier")))
    return [row[0].strip() for row in result["rows"] if row and row[0].strip()]


def image_group(host: Any, image_group_id: str) -> Optional[Dict[str, str]]:
    """Return the image group ``image_group_id`` (or None)."""
    return _group(host, SQL["image_group_by_id"].format(
        image_group_id=_require(IMAGE_GROUP_ID_RE, image_group_id, "image_group_id")))


def newest_built_image_group(host: Any) -> Optional[Dict[str, str]]:
    """Return the newest image group in BUILT state (or None)."""
    return _group(host, SQL["newest_built_image_group"])


def image_count(host: Any, image_group_id: str) -> int:
    """Return how many images belong to an image group."""
    result = query(host, SQL["image_count"].format(
        image_group_id=_require(IMAGE_GROUP_ID_RE, image_group_id, "image_group_id")))
    return int(result["rows"][0][0]) if result["success"] and result["rows"] else 0


def stage_rows(host: Any, job_id: str, stages: Sequence[str]) -> List[Dict[str, str]]:
    """Return rows for ``stages`` in order (missing stages as NOT CREATED)."""
    found = get_stages(host, job_id)
    return [found.get(name, {"stage_name": name, "stage_state": "NOT CREATED",
                             "attempt": "", "error_code": "", "error_summary": "",
                             "log_file_path": "", "started_at": ""})
            for name in stages]
