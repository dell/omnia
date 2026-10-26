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

TLS follows Omnia: the BuildStream API is verified against the certificate
build_stream.yml generates (``<OMNIA_DATA_PATH>/build_stream_ssl/ssl/
bs_cert.pem``, the same certificate the pipelines pass to ``curl --cacert``).
GitLab is not verified, like Omnia's own playbooks (``validate_certs:
false``); its CA lives on the GitLab host.

Secrets stay in memory: they are never logged, placed on a command line or
included in returned error text.
"""

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

import yaml

from omnia_auto import read_remote_yaml

from .probe_func import data_path, domain_input_path, run_cmd
from ..vars.common_vars import (
    BSM_API_GRANT_TYPE,
    BSM_API_HEALTH_PATH,
    BSM_API_HEALTHY,
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
    HTTP_TIMEOUT,
    OMNIA_ENV_FILE,
)


def _bsm_tls(host: Any) -> ssl.SSLContext:
    """Return a context that trusts only the BuildStream API certificate.

    Raises:
        RuntimeError: When the certificate cannot be read or loaded.
    """
    path = f"{data_path(host)}/{BSM_TLS_CERT}"
    result = run_cmd(host, "cat_file", path=path)
    if result.rc != 0:
        raise RuntimeError(f"BuildStream API certificate {path} not found (rc={result.rc})")
    try:
        context = ssl.create_default_context(cadata=result.stdout)
    except ssl.SSLError as exc:
        raise RuntimeError(f"BuildStream API certificate {path} is invalid: {exc}") from exc
    # bs_cert.pem is self-signed: trust the leaf itself as the anchor.
    context.verify_flags |= ssl.VerifyFlags.VERIFY_X509_PARTIAL_CHAIN
    return context


def _gitlab_tls() -> ssl.SSLContext:
    """Return the unverified GitLab context Omnia's own playbooks use."""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def http_json(tls: ssl.SSLContext, method: str, url: str,
              headers: Optional[Dict[str, str]] = None,
              payload: Optional[Dict[str, Any]] = None,
              form: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Send an HTTP request over ``tls`` and decode a JSON response.

    Returns:
        Dict with keys: success (2xx), status, data (decoded JSON or text),
        error (no request headers or bodies are echoed).
    """
    body = None
    request_headers = dict(headers or {})
    if payload is not None:
        body = json.dumps(payload).encode()
        request_headers["Content-Type"] = "application/json"
    elif form is not None:
        body = urllib.parse.urlencode(form).encode()
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(  # nosec B310
            request, context=tls, timeout=HTTP_TIMEOUT
        ) as response:
            raw = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as exc:
        return {"success": False, "status": exc.code, "data": None,
                "error": f"HTTP {exc.code} {exc.reason} for {method} {url}"}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"success": False, "status": 0, "data": None,
                "error": f"{method} {url} failed: {exc}"}
    try:
        data = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        data = raw
    return {"success": True, "status": status, "data": data, "error": ""}


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
        bsm_tls = _bsm_tls(host)
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
        "bsm_tls": bsm_tls,
        "gitlab_tls": _gitlab_tls(),
    }


def check_bsm_health(context: Dict[str, Any]) -> Dict[str, Any]:
    """Call the BuildStream ``/health`` endpoint.

    Returns:
        Dict with keys: success, url, status, error.
    """
    url = f"{context['bsm_url']}{BSM_API_HEALTH_PATH}"
    response = http_json(context["bsm_tls"], "GET", url)
    healthy = response["success"] and isinstance(response["data"], dict) and (
        response["data"].get("status") == BSM_API_HEALTHY
    )
    return {
        "success": healthy,
        "url": url,
        "status": (response["data"] or {}).get("status") if healthy else response["status"],
        "error": "" if healthy else (response["error"] or f"unexpected body: {response['data']}"),
    }


def _bsm_access_token(context: Dict[str, Any]) -> Dict[str, Any]:
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
        Dict with keys: success, job_state, stages ({name: state}),
        log_paths ({name: path}), error.
    """
    token = _bsm_access_token(context)
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
        "job_state": response["data"].get("job_state", ""),
        "stages": {item.get("stage_name"): item.get("stage_state") for item in stages},
        "log_paths": {item.get("stage_name"): item.get("log_file_path") or ""
                      for item in stages},
        "error": "",
    }
