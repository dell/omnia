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
Build Stream — GitLab Project and Repository Verification Functions.

Functions to verify the GitLab project, its visibility and default branch,
repository files, CI/CD pipeline variables and uploaded domain inputs.

API calls run in this process over TLS verified against the GitLab CA; the
root token stays in memory (never on a command line or in output).
"""

import urllib.parse
from typing import Any, Dict

from omnia_auto import Symbols

from library.functions.gitlab_ssh_func import (
    get_gitlab_config,
    get_gitlab_root_token,
    gitlab_tls,
)
from library.vars.common_vars import (
    GITLAB_API_VERSION,
    GITLAB_INPUT_REPO_DIR,
    GITLAB_PIPELINE_VARIABLES,
    GITLAB_UPLOADED_INPUT_FILES,
    GITLAB_VISIBILITY_LEVELS,
)

from .http_func import http_json


_PROJECT_CACHE: Dict[str, Dict[str, Any]] = {}


def _get_gitlab_project(host) -> Dict[str, Any]:
    """Return the GitLab project from the REST API (cached per session).

    One API call replaces a ``gitlab-rails runner`` boot (about 40 seconds)
    per check.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, project (API JSON), project_name, error.
    """
    gitlab_config = get_gitlab_config(host)
    project_name = gitlab_config.get("gitlab_project_name", "omnia-catalog")
    cache_key = f"{gitlab_config.get('gitlab_host', '')}/{project_name}"
    if cache_key in _PROJECT_CACHE:
        return _PROJECT_CACHE[cache_key]
    result = {"success": False, "project": {}, "project_name": project_name, "error": ""}
    ctx = _api_context(host, gitlab_config)
    if ctx.get("error"):
        result["error"] = ctx["error"]
        return result
    response = http_json(ctx["tls"], "GET", f"{ctx['api_url']}/projects/{ctx['project_id']}",
                         headers=ctx["headers"])
    project = response["data"] if response["success"] else {}
    if not isinstance(project, dict) or not project.get("id"):
        result["error"] = f"Project '{project_name}' not found via the GitLab API"
        return result
    result.update(success=True, project=project)
    _PROJECT_CACHE[cache_key] = result
    return result



def check_gitlab_project_exists(host) -> Dict[str, Any]:
    """Verify the GitLab project exists.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, project_name, project_id, details,
        error.
    """
    gitlab_config = get_gitlab_config(host)
    project_name = gitlab_config.get("gitlab_project_name", "omnia-catalog")

    result = {
        "success": False,
        "project_name": project_name,
        "project_id": None,
        "details": "",
        "error": "",
    }

    project = _get_gitlab_project(host)
    if not project["success"]:
        result["error"] = project["error"]
        return result

    project_id = project["project"]["id"]
    result["project_id"] = int(project_id)
    result["success"] = True
    result["details"] = f"Project '{project_name}' exists (ID: {project_id})"
    return result


def check_gitlab_project_visibility(host) -> Dict[str, Any]:
    """Verify GitLab project visibility is configured correctly.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, expected, actual, details, error.
    """
    gitlab_config = get_gitlab_config(host)
    expected = gitlab_config.get("project_visibility", "private")

    result = {
        "success": False,
        "expected": expected,
        "actual": "",
        "details": "",
        "error": "",
    }

    project = _get_gitlab_project(host)
    if not project["success"]:
        result["error"] = f"Failed to query visibility: {project['error']}"
        return result

    result["actual"] = str(project["project"].get("visibility", ""))
    if expected not in GITLAB_VISIBILITY_LEVELS:
        result["error"] = f"Unsupported project_visibility '{expected}'"
        return result
    if result["actual"] == expected:
        result["success"] = True
        result["details"] = f"Visibility: {result['actual']}"
    else:
        result["error"] = (
            f"Expected {expected}, got {result['actual']}"
        )
    return result


def check_gitlab_default_branch(host) -> Dict[str, Any]:
    """Verify GitLab project default branch is configured correctly.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, expected, actual, details, error.
    """
    gitlab_config = get_gitlab_config(host)
    expected = gitlab_config.get("default_branch", "main")

    result = {
        "success": False,
        "expected": expected,
        "actual": "",
        "details": "",
        "error": "",
    }

    project = _get_gitlab_project(host)
    if not project["success"]:
        result["error"] = f"Failed to query branch: {project['error']}"
        return result

    result["actual"] = str(project["project"].get("default_branch", ""))
    if result["actual"] == expected:
        result["success"] = True
        result["details"] = f"Default branch: {result['actual']}"
    else:
        result["error"] = (
            f"Expected {expected}, got {result['actual']}"
        )
    return result


def _api_context(host, gitlab_config: Dict[str, str]) -> Dict[str, Any]:
    """Return the GitLab API base URL, auth header, verified TLS, project and branch."""
    token_result = get_gitlab_root_token(host)
    if not token_result["success"]:
        return {"error": f"Failed to get GitLab token: {token_result['error']}"}
    try:
        tls = gitlab_tls(host)
    except RuntimeError as exc:
        return {"error": str(exc)}
    project_name = gitlab_config.get("gitlab_project_name", "omnia-catalog")
    return {
        "api_url": (f"https://{gitlab_config.get('gitlab_host', '')}:"
                    f"{gitlab_config.get('gitlab_https_port', '443')}/api/{GITLAB_API_VERSION}"),
        "headers": {"PRIVATE-TOKEN": token_result["token"]},
        "tls": tls,
        "project_id": urllib.parse.quote(f"root/{project_name}", safe=""),
        "branch": gitlab_config.get("default_branch", "main"),
        "error": "",
    }


def _get_gitlab_api_context(host) -> Dict[str, Any]:
    """Return the API context once the project is known to exist.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with api_url, headers, tls, project_id, branch, or error.
    """
    gitlab_config = get_gitlab_config(host)
    project_result = _get_gitlab_project(host)
    if not project_result["success"]:
        return {"error": project_result["error"]}
    return _api_context(host, gitlab_config)


def check_gitlab_repo_file_exists(
    host, file_path: str
) -> Dict[str, Any]:
    """Verify a file exists in the GitLab repository.

    Args:
        host: Testinfra host connection.
        file_path: Path of the file in the repository.

    Returns:
        Dict with keys: success, file, details, error.
    """
    result = {
        "success": False,
        "file": file_path,
        "details": "",
        "error": "",
    }

    ctx = _get_gitlab_api_context(host)
    if ctx.get("error"):
        result["error"] = ctx["error"]
        return result

    encoded_path = urllib.parse.quote(file_path, safe="")
    query = urllib.parse.urlencode({"ref": ctx["branch"]})
    response = http_json(
        ctx["tls"], "GET",
        f"{ctx['api_url']}/projects/{ctx['project_id']}/repository/files/{encoded_path}"
        f"/raw?{query}",
        headers=ctx["headers"],
    )
    if response["success"]:
        result["success"] = True
        result["details"] = f"{file_path} exists in repo"
    else:
        result["error"] = f"{file_path} not found (HTTP {response['status'] or 'N/A'})"
    return result


def check_gitlab_pipeline_variables(host) -> Dict[str, Any]:
    """Verify GitLab CI/CD pipeline variables are configured.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, found, missing, total, details, error.
    """
    result = {
        "success": False,
        "found": [],
        "missing": [],
        "total": len(GITLAB_PIPELINE_VARIABLES),
        "details": "",
        "error": "",
    }

    ctx = _get_gitlab_api_context(host)
    if ctx.get("error"):
        result["error"] = ctx["error"]
        return result

    response = http_json(
        ctx["tls"], "GET",
        f"{ctx['api_url']}/projects/{ctx['project_id']}/variables?per_page=100",
        headers=ctx["headers"],
    )
    variables = response["data"] if response["success"] else None
    if not isinstance(variables, list):
        result["error"] = f"Failed to list pipeline variables: {response['error']}"
        return result
    var_keys = {item.get("key") for item in variables if isinstance(item, dict)}

    for var_name in GITLAB_PIPELINE_VARIABLES:
        if var_name in var_keys:
            result["found"].append(var_name)
        else:
            result["missing"].append(var_name)

    result["success"] = len(result["missing"]) == 0
    result["details"] = (
        f"{len(result['found'])}/{result['total']} variables configured"
    )
    return result


def check_omnia_env_in_repo(host) -> Dict[str, Any]:
    """Verify omnia.env exists in the GitLab repository.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    file_result = check_gitlab_repo_file_exists(host, "omnia.env")
    if not file_result["success"]:
        return {
            "success": False,
            "details": "",
            "error": "omnia.env not found in GitLab repo",
        }
    return {
        "success": True,
        "details": "omnia.env exists in GitLab repo",
        "error": "",
    }


def _gitlab_repo_dir_files(ctx: Dict[str, Any], dir_path: str) -> Any:
    """Return the file names in a GitLab repository directory (None on API error)."""
    query = urllib.parse.urlencode({"path": dir_path, "ref": ctx["branch"], "per_page": 100})
    response = http_json(
        ctx["tls"], "GET",
        f"{ctx['api_url']}/projects/{ctx['project_id']}/repository/tree?{query}",
        headers=ctx["headers"],
    )
    data = response["data"] if response["success"] else None
    if not isinstance(data, list):
        return None
    return {item.get("name") for item in data if item.get("type") == "blob"}


def check_domain_input_dirs(host) -> Dict[str, Any]:
    """Verify every domain input file uploaded by --tags execute is in the repo.

    Lists input/<domain>/ once per domain (repo_manager, image_build_manager,
    orchestrator) and checks each file of GITLAB_UPLOADED_INPUT_FILES.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, fields (one line per file), found, missing,
        failures, error.
    """
    result = {"success": False, "fields": [], "found": [], "missing": [],
              "failures": [], "error": ""}
    ctx = _get_gitlab_api_context(host)
    if ctx.get("error"):
        result["error"] = ctx["error"]
        return result

    for domain, files in GITLAB_UPLOADED_INPUT_FILES.items():
        dir_path = f"{GITLAB_INPUT_REPO_DIR}/{domain}"
        present = _gitlab_repo_dir_files(ctx, dir_path)
        for name in files:
            path = f"{dir_path}/{name}"
            if present is None:
                state, ok = "API ERROR (directory not listed)", False
            else:
                ok = name in present
                state = "present" if ok else "MISSING"
            result["fields"].append((f"{Symbols.CHECK if ok else Symbols.CROSS} {path}", state))
            result["found" if ok else "missing"].append(path)
            if not ok:
                result["failures"].append(f"{path}: {state}")

    result["success"] = not result["missing"]
    result["error"] = "; ".join(result["failures"])
    return result
