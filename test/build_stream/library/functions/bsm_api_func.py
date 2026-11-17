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

"""BuildStream runtime context, HTTP transport and BuildStream API calls.

Every endpoint, port and secret is read at runtime from the OIM:

- build_stream_config.yml  -> BuildStream API and GitLab host/port/branch
- build_stream_credentials.yml (vault) -> GitLab token and project ID
- GitLab CI/CD variables -> BSM OAuth client used by the pipelines

TLS is always verified: the BuildStream API against the certificate
build_stream.yml generates (``<OMNIA_DATA_PATH>/build_stream/ssl/
bs_cert.pem``, the same certificate the pipelines pass to ``curl --cacert``),
GitLab against the CA hosted_gitlab generates (read from the GitLab host over
the passwordless SSH the product sets up, see ``gitlab_ssh_func.gitlab_tls``).

Secrets stay in memory: they are never logged, placed on a command line or
included in returned error text.
"""

import ssl
import urllib.parse
from typing import Any, Dict

import yaml

from omnia_auto import read_remote_yaml

from .execute_probe_func import data_path, domain_input_path, run_cmd
from .gitlab_ssh_func import gitlab_tls
from .http_func import http_json, tls_from_pem
from ..vars.execute_vars import (
    BSM_API_GRANT_TYPE,
    BSM_API_ARTIFACT_PATH,
    BSM_API_JOB_PATH,
    BSM_API_TOKEN_PATH,
    BSM_CI_CLIENT_ID_VAR,
    BSM_CI_CLIENT_SECRET_VAR,
    BSM_CONFIG_FILE,
    BSM_CONFIG_KEYS,
    BSM_CREDENTIAL_KEYS,
    BSM_CREDENTIALS_FILE,
    BSM_CREDENTIALS_KEY,
    BSM_DOMAIN,
    BSM_TLS_CERT,
    GITLAB_API,
    OMNIA_ENV_FILE,
)


def bsm_tls(host: Any) -> ssl.SSLContext:
    """Return a context that trusts only the BuildStream API certificate.

    Raises:
        RuntimeError: When the certificate cannot be read or loaded.
    """
    path = f"{data_path(host)}/{BSM_TLS_CERT}"
    result = run_cmd(host, "cat_file", path=path)
    if result.rc != 0:
        raise RuntimeError(f"BuildStream API certificate {path} not found (rc={result.rc})")
    try:
        # bs_cert.pem is self-signed: trust the leaf itself as the anchor.
        return tls_from_pem(result.stdout, leaf_is_anchor=True)
    except ssl.SSLError as exc:
        raise RuntimeError(f"BuildStream API certificate {path} is invalid: {exc}") from exc


def _read_credentials(host: Any, input_dir: str) -> Dict[str, Any]:
    """Decrypt build_stream_credentials.yml with its vault key on the OIM."""
    result = run_cmd(
        host, "vault_view",
        env_file=OMNIA_ENV_FILE,
        path=f"{input_dir}/{BSM_CREDENTIALS_FILE}",
        key=f"{input_dir}/{BSM_CREDENTIALS_KEY}",
    )
    if result.rc != 0:
        raise RuntimeError(
            f"Cannot decrypt {input_dir}/{BSM_CREDENTIALS_FILE} (rc={result.rc})"
        )
    data = yaml.safe_load(result.stdout) or {}
    if not isinstance(data, dict):
        raise RuntimeError(f"{BSM_CREDENTIALS_FILE} is not a mapping")
    return data


def load_bsm_context(host: Any) -> Dict[str, Any]:
    """Resolve BuildStream/GitLab endpoints, credentials and TLS from the OIM.

    Returns:
        Dict with keys: success, error and, on success, config (parsed
        build_stream_config.yml), input_dir, bsm_url, gitlab_url,
        gitlab_api (project API base), gitlab_branch, gitlab_headers,
        bsm_tls, gitlab_tls.
    """
    try:
        input_dir = domain_input_path(host, BSM_DOMAIN)
        config = read_remote_yaml(host, f"{input_dir}/{BSM_CONFIG_FILE}")
        credentials = _read_credentials(host, input_dir)
        bsm_tls_context = bsm_tls(host)
        gitlab_context = gitlab_tls(host)
    except (RuntimeError, ValueError, yaml.YAMLError) as exc:
        return {"success": False, "error": str(exc)}

    missing = [
        key for key in ("api_host", "api_port", "gitlab_host", "gitlab_port")
        if not config.get(BSM_CONFIG_KEYS[key])
    ] + [key for key, name in BSM_CREDENTIAL_KEYS.items() if not credentials.get(name)]
    if missing:
        return {"success": False,
                "error": f"BuildStream configuration incomplete: {', '.join(missing)}"}

    gitlab_url = (f"https://{config[BSM_CONFIG_KEYS['gitlab_host']]}:"
                  f"{config[BSM_CONFIG_KEYS['gitlab_port']]}")
    project_id = urllib.parse.quote(
        str(credentials[BSM_CREDENTIAL_KEYS["gitlab_project_id"]]), safe=""
    )
    return {
        "success": True,
        "error": "",
        "config": config,
        "input_dir": input_dir,
        "bsm_url": (f"https://{config[BSM_CONFIG_KEYS['api_host']]}:"
                    f"{config[BSM_CONFIG_KEYS['api_port']]}"),
        "gitlab_url": gitlab_url,
        "gitlab_api": f"{gitlab_url}{GITLAB_API}/projects/{project_id}",
        "gitlab_branch": config.get(BSM_CONFIG_KEYS["gitlab_branch"]) or "main",
        "gitlab_headers": {
            "PRIVATE-TOKEN": str(credentials[BSM_CREDENTIAL_KEYS["gitlab_token"]])
        },
        "bsm_tls": bsm_tls_context,
        "gitlab_tls": gitlab_context,
    }


def bsm_access_token(context: Dict[str, Any]) -> Dict[str, Any]:
    """Obtain an OAuth token with the pipeline client stored in GitLab CI."""
    variables = http_json(
        context["gitlab_tls"], "GET", f"{context['gitlab_api']}/variables?per_page=100",
        headers=context["gitlab_headers"],
    )
    if not variables["success"]:
        return {"success": False, "token": "", "error": variables["error"]}
    values = {item.get("key"): item.get("value") for item in variables["data"] or []}
    client_id = values.get(BSM_CI_CLIENT_ID_VAR)
    client_secret = values.get(BSM_CI_CLIENT_SECRET_VAR)
    if not client_id or not client_secret:
        return {"success": False, "token": "",
                "error": f"{BSM_CI_CLIENT_ID_VAR}/{BSM_CI_CLIENT_SECRET_VAR} "
                         "are not set in GitLab CI/CD variables (no pipeline has "
                         "registered a client yet)"}
    response = http_json(
        context["bsm_tls"], "POST", f"{context['bsm_url']}{BSM_API_TOKEN_PATH}",
        form={"grant_type": BSM_API_GRANT_TYPE, "client_id": client_id,
              "client_secret": client_secret},
    )
    token = (response["data"] or {}).get("access_token") if response["success"] else ""
    if not token:
        return {"success": False, "token": "",
                "error": response["error"] or "token response has no access_token"}
    return {"success": True, "token": token, "error": ""}


def get_api_job(context: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    """Read ``GET /api/v1/jobs/{job_id}`` from the BuildStream API.

    Returns:
        Dict with keys: success, job_id, job_state, stages ({name: state}),
        log_paths ({name: path}), error.
    """
    token = bsm_access_token(context)
    if not token["success"]:
        return {"success": False, "job_state": "", "stages": {}, "log_paths": {},
                "error": token["error"]}
    response = http_json(
        context["bsm_tls"], "GET",
        f"{context['bsm_url']}{BSM_API_JOB_PATH.format(job_id=job_id)}",
        headers={"Authorization": f"Bearer {token['token']}"},
    )
    if not response["success"] or not isinstance(response["data"], dict):
        return {"success": False, "job_state": "", "stages": {}, "log_paths": {},
                "error": response["error"] or "unexpected job response"}
    stages = response["data"].get("stages") or []
    return {
        "success": True,
        "job_id": response["data"].get("job_id", ""),
        "job_state": response["data"].get("job_state", ""),
        "stages": {item.get("stage_name"): item.get("stage_state") for item in stages},
        "log_paths": {item.get("stage_name"): item.get("log_file_path") or ""
                      for item in stages},
        "error": "",
    }


def get_api_artifact(context: Dict[str, Any], job_id: str, label: str) -> Dict[str, Any]:
    """Read a JSON job artifact (``node-results``, ``failed-nodes``) from the API.

    Returns:
        Dict with keys: success, exists (False on HTTP 404), data, error.
    """
    token = bsm_access_token(context)
    if not token["success"]:
        return {"success": False, "exists": False, "data": None, "error": token["error"]}
    response = http_json(
        context["bsm_tls"], "GET",
        f"{context['bsm_url']}{BSM_API_ARTIFACT_PATH.format(job_id=job_id, label=label)}",
        headers={"Authorization": f"Bearer {token['token']}"},
    )
    if response["status"] == 404:
        return {"success": True, "exists": False, "data": None, "error": ""}
    return {"success": response["success"], "exists": response["success"],
            "data": response["data"], "error": response["error"]}
