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

"""GitLab REST API operations on the BuildStream catalog project."""

import base64
import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional

from .api_func import http_json
from ..messages.system_test_msgs import PROGRESS_MSGS as PROGRESS
from ..vars.common_vars import (
    GITLAB_BUSY_STATUSES,
    PIPELINE_DETECT_INTERVAL,
    PIPELINE_DETECT_TIMEOUT,
)


def _get(context: Dict[str, Any], path: str) -> Dict[str, Any]:
    """GET a project API path."""
    return http_json(context["gitlab_tls"], "GET", f"{context['gitlab_api']}{path}",
                     headers=context["gitlab_headers"])


def _post(context: Dict[str, Any], path: str,
          payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """POST to a project API path."""
    return http_json(context["gitlab_tls"], "POST", f"{context['gitlab_api']}{path}",
                     headers=context["gitlab_headers"], payload=payload)


def _encoded(file_path: str) -> str:
    """URL-encode a repository file path."""
    return urllib.parse.quote(file_path, safe="")


def check_gitlab_project(context: Dict[str, Any]) -> Dict[str, Any]:
    """Read the catalog project to prove GitLab and the token work.

    Returns:
        Dict with keys: success, name, url, error.
    """
    response = _get(context, "")
    data = response["data"] if isinstance(response["data"], dict) else {}
    return {"success": response["success"], "name": data.get("path_with_namespace", ""),
            "url": data.get("web_url", context["gitlab_url"]), "error": response["error"]}


def get_file(context: Dict[str, Any], file_path: str) -> Dict[str, Any]:
    """Return the decoded content of a repository file on the default branch.

    Returns:
        Dict with keys: success, content, last_commit_id, error.
    """
    response = _get(context, f"/repository/files/{_encoded(file_path)}"
                             f"?ref={urllib.parse.quote(context['gitlab_branch'])}")
    if not response["success"] or not isinstance(response["data"], dict):
        return {"success": False, "content": "", "last_commit_id": "",
                "error": response["error"] or f"{file_path} not found"}
    content = base64.b64decode(response["data"].get("content", "")).decode()
    return {"success": True, "content": content,
            "last_commit_id": response["data"].get("last_commit_id", ""), "error": ""}


def commit_file(context: Dict[str, Any], file_path: str, content: str,
                message: str) -> Dict[str, Any]:
    """Update a repository file on the default branch.

    Returns:
        Dict with keys: success, commit_id, error.
    """
    response = http_json(
        context["gitlab_tls"], "PUT",
        f"{context['gitlab_api']}/repository/files/{_encoded(file_path)}",
        headers=context["gitlab_headers"],
        payload={"branch": context["gitlab_branch"], "content": content,
                 "commit_message": message},
    )
    if not response["success"]:
        return {"success": False, "commit_id": "", "error": response["error"]}
    latest = latest_commit(context, file_path)
    return {"success": latest["success"], "commit_id": latest["commit_id"],
            "error": latest["error"]}


def latest_commit(context: Dict[str, Any], file_path: str,
                  since: str = "") -> Dict[str, Any]:
    """Return the newest commit on the default branch touching ``file_path``.

    Returns:
        Dict with keys: success, commit_id, title, created_at, error.
        commit_id is empty when no commit matches.
    """
    query = {"ref_name": context["gitlab_branch"], "path": file_path, "per_page": 1}
    if since:
        query["since"] = since
    response = _get(context, f"/repository/commits?{urllib.parse.urlencode(query)}")
    commits = response["data"] if response["success"] and isinstance(response["data"], list) else []
    first = commits[0] if commits else {}
    return {"success": response["success"], "commit_id": first.get("id", ""),
            "title": first.get("title", ""), "created_at": first.get("created_at", ""),
            "error": response["error"]}


def list_pipelines(context: Dict[str, Any], **query: Any) -> List[Dict[str, Any]]:
    """Return project pipelines matching the query (newest first)."""
    query.setdefault("per_page", 20)
    response = _get(context, f"/pipelines?{urllib.parse.urlencode(query)}")
    return response["data"] if response["success"] and isinstance(response["data"], list) else []


def get_pipeline(context: Dict[str, Any], pipeline_id: int) -> Dict[str, Any]:
    """Return one pipeline (empty dict when it cannot be read)."""
    response = _get(context, f"/pipelines/{int(pipeline_id)}")
    return response["data"] if response["success"] and isinstance(response["data"], dict) else {}


def pipeline_jobs(context: Dict[str, Any], pipeline_id: int) -> List[Dict[str, Any]]:
    """Return the jobs of a pipeline."""
    response = _get(context, f"/pipelines/{int(pipeline_id)}/jobs?per_page=100")
    return response["data"] if response["success"] and isinstance(response["data"], list) else []


def pipeline_bridges(context: Dict[str, Any], pipeline_id: int) -> List[Dict[str, Any]]:
    """Return the trigger (bridge) jobs of a pipeline."""
    response = _get(context, f"/pipelines/{int(pipeline_id)}/bridges?per_page=100")
    return response["data"] if response["success"] and isinstance(response["data"], list) else []


def downstream_pipeline(context: Dict[str, Any], pipeline_id: int,
                        bridge_name: str) -> Dict[str, Any]:
    """Return the downstream pipeline created by ``bridge_name`` (or {})."""
    for bridge in pipeline_bridges(context, pipeline_id):
        if bridge.get("name") == bridge_name:
            return bridge.get("downstream_pipeline") or {}
    return {}


def busy_pipelines(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return running or pending pipelines."""
    return [p for p in list_pipelines(context) if p.get("status") in GITLAB_BUSY_STATUSES]


def cancel_pipeline(context: Dict[str, Any], pipeline_id: int) -> Dict[str, Any]:
    """Cancel a pipeline. Returns http_json's result dict."""
    return _post(context, f"/pipelines/{int(pipeline_id)}/cancel")


def play_job(context: Dict[str, Any], job_id: int) -> Dict[str, Any]:
    """Play a manual job. Returns http_json's result dict."""
    return _post(context, f"/jobs/{int(job_id)}/play")


def wait_for_pipeline(context: Dict[str, Any], commit_id: str,
                      emit: Callable[[str], None],
                      timeout: int = PIPELINE_DETECT_TIMEOUT) -> Dict[str, Any]:
    """Wait until GitLab creates the pipeline for ``commit_id``.

    Returns:
        Dict with keys: success, pipeline (dict), error.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        pipelines = list_pipelines(context, sha=commit_id)
        if pipelines:
            return {"success": True, "pipeline": pipelines[0], "error": ""}
        emit(PROGRESS["pipeline_detect_wait"].format(commit=commit_id[:8]))
        time.sleep(PIPELINE_DETECT_INTERVAL)
    return {"success": False, "pipeline": {},
            "error": f"no pipeline created for commit {commit_id[:8]} within {timeout}s"}


def wait_for_downstream(context: Dict[str, Any], pipeline_id: int, bridge_name: str,
                        emit: Callable[[str], None],
                        timeout: int = PIPELINE_DETECT_TIMEOUT) -> Dict[str, Any]:
    """Wait for ``bridge_name`` in ``pipeline_id`` to create its child pipeline.

    Returns:
        Dict with keys: success, pipeline (dict), error.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        child = downstream_pipeline(context, pipeline_id, bridge_name)
        if child.get("id"):
            return {"success": True, "pipeline": child, "error": ""}
        parent = get_pipeline(context, pipeline_id)
        if parent.get("status") in ("failed", "canceled", "skipped"):
            return {"success": False, "pipeline": {},
                    "error": f"pipeline #{pipeline_id} {parent['status']} before "
                             f"'{bridge_name}' started"}
        emit(PROGRESS["bridge_wait"].format(bridge=bridge_name, pipeline_id=pipeline_id))
        time.sleep(PIPELINE_DETECT_INTERVAL)
    return {"success": False, "pipeline": {},
            "error": f"'{bridge_name}' did not start within {timeout}s"}


def find_job(jobs: List[Dict[str, Any]], name: Optional[str] = None,
             stage: Optional[str] = None) -> List[Dict[str, Any]]:
    """Filter pipeline jobs by name and/or stage."""
    return [job for job in jobs
            if (name is None or job.get("name") == name)
            and (stage is None or job.get("stage") == stage)]
