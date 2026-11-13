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

"""Pipeline log query API helpers for BuildStream FVT (ER-BSM-003).

Fixture logs are planted only for disposable jobs created by the test.
Identifiers are validated against strict patterns before they are placed in a
shell or SQL command, because ``psql -c`` does not support bound parameters.
"""

import base64
import re
import shlex
import uuid
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from omnia_auto import run_on_host

from library.functions import nft_func, pipeline_func
from library.functions._config_helpers import resolve_omnia_path

ALLOWED_STAGES = frozenset({
    "parse-catalog", "create-local-repository", "build-image",
    "validate", "restart", "upload", "deploy",
})
FIXTURE_LOG_NAME = re.compile(r"^fvt_[a-z0-9_-]{1,64}\.log$")
SAFE_STORED_PATH = re.compile(r"^/[A-Za-z0-9._/-]{1,500}$")


def _validated_job_id(job_id: str) -> str:
    """Return the canonical UUID or raise ValueError."""
    return str(uuid.UUID(str(job_id)))


def _validated_stage(stage: str) -> str:
    """Return the stage name when it is a known BSM stage."""
    if stage not in ALLOWED_STAGES:
        raise ValueError(f"Unsupported stage: {stage}")
    return stage


def query_job_logs(
    host, job_id: str, params: Optional[Dict[str, Any]] = None, token: Optional[str] = None
) -> Dict[str, Any]:
    """Call GET /jobs/{job_id}/logs with the installed client token by default."""
    context = nft_func.get_bsm_context(host)
    query = f"?{urlencode(params)}" if params else ""
    return nft_func.bsm_request(
        host, "GET", f"/jobs/{job_id}/logs{query}",
        token=context["token"] if token is None else token,
    )


def get_job(host, job_id: str) -> Dict[str, Any]:
    """Call GET /jobs/{job_id} with the installed client token."""
    context = nft_func.get_bsm_context(host)
    return nft_func.bsm_request(host, "GET", f"/jobs/{job_id}", token=context["token"])


def _set_stage(host, job_id: str, stage: str, state: str, stored_path: Optional[str]) -> Dict:
    """Update one stage row of a disposable job (validated inputs only)."""
    job = _validated_job_id(job_id)
    name = _validated_stage(stage)
    if state not in {"PENDING", "COMPLETED"}:
        raise ValueError(f"Unsupported state: {state}")
    if stored_path is None:
        path_sql = "NULL"
    elif SAFE_STORED_PATH.match(stored_path) and ".." not in stored_path:
        path_sql = f"'{stored_path}'"
    else:
        raise ValueError("Unsafe stored path")
    sql = (
        f"UPDATE job_stages SET stage_state='{state}', log_file_path={path_sql} "
        f"WHERE job_id='{job}' AND stage_name='{name}';"
    )
    return pipeline_func._exec_psql(host, sql)  # pylint: disable=protected-access


def plant_stage_log(host, job_id: str, stage: str, file_name: str, content: bytes) -> Dict:
    """Publish fixture content as a completed stage log of a disposable job.

    The file is written where the playbook watcher publishes logs on the OIM
    and the stage row stores that host path, exactly as the result poller does.
    """
    job = _validated_job_id(job_id)
    if not FIXTURE_LOG_NAME.match(file_name):
        raise ValueError("Fixture log names must match fvt_<name>.log")
    job_dir = resolve_omnia_path(host, "build_stream", "log", job)
    target = f"{job_dir}/{file_name}"
    encoded = base64.b64encode(content).decode("ascii")
    write = run_on_host(
        host,
        f"mkdir -p -- {shlex.quote(job_dir)} && printf %s {shlex.quote(encoded)} "
        f"| base64 -d > {shlex.quote(target)}",
    )
    if write.rc != 0:
        return {"success": False, "path": target, "error": f"write failed rc={write.rc}"}
    updated = _set_stage(host, job, stage, "COMPLETED", target)
    return {"success": updated["success"], "path": target, "error": updated["error"]}


def point_stage_at(host, job_id: str, stage: str, stored_path: str) -> Dict:
    """Store an arbitrary (validated) log path on a disposable job's stage."""
    return _set_stage(host, job_id, stage, "COMPLETED", stored_path)


def read_remote_file(host, path: str) -> Dict[str, Any]:
    """Return the raw content of a planted fixture file."""
    result = run_on_host(host, f"base64 -w0 -- {shlex.quote(path)}")
    if result.rc != 0:
        return {"success": False, "content": b"", "error": f"read failed rc={result.rc}"}
    return {"success": True, "content": base64.b64decode(result.stdout.strip()), "error": ""}


def delete_planted_log(host, job_id: str, file_name: str) -> bool:
    """Delete one planted fixture file of a disposable job."""
    job = _validated_job_id(job_id)
    if not FIXTURE_LOG_NAME.match(file_name):
        raise ValueError("Fixture log names must match fvt_<name>.log")
    target = f"{resolve_omnia_path(host, 'build_stream', 'log', job)}/{file_name}"
    return run_on_host(host, f"rm -f -- {shlex.quote(target)}").rc == 0


def remove_planted_logs(host, job_id: str, stages) -> None:
    """Delete fixture files and reset the disposable job's stage rows."""
    job = _validated_job_id(job_id)
    job_dir = resolve_omnia_path(host, "build_stream", "log", job)
    run_on_host(host, f"rm -f -- {shlex.quote(job_dir)}/fvt_*.log")
    for stage in stages:
        _set_stage(host, job, stage, "PENDING", None)
