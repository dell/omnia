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

"""GitLab mode resolution and the external GitLab connection.

``build_stream_config.yml`` selects how BuildStream uses GitLab:

- ``hosted``: Omnia installs GitLab CE and a runner on ``gitlab_host`` and the
  suites reach it over SSH (the behavior of every hosted-mode test);
- ``external``: a customer-managed GitLab reached only through its REST API with
  the personal access token ``gitlab_api_token``.

The execute scenario reads the mode from the input file on the OIM, so the
same ``execute`` tag verifies a hosted GitLab exactly as before and an
external GitLab with its own checks. Secrets stay in memory: they are never
logged, placed on a command line or included in returned error text.
"""

import ssl
import urllib.parse
from typing import Any, Dict

import yaml

from omnia_auto import read_remote_yaml

from library.functions.probe_func import summarize_probes
from library.gitlab_inputs import (
    external_settings,
    gitlab_mode_of,
    mode_input_probes,
)

from .execute_probe_func import domain_input_path, run_cmd
from .http_func import tls_from_pem
from ..vars.execute_vars import (
    BSM_CONFIG_FILE,
    BSM_CREDENTIALS_FILE,
    BSM_CREDENTIALS_KEY,
    BSM_DOMAIN,
    GITLAB_API,
    GITLAB_EXTERNAL_CONFIG_KEYS,
    GITLAB_EXTERNAL_PROJECT_ID_KEY,
    GITLAB_EXTERNAL_TOKEN_KEY,
    GITLAB_MODE_EXTERNAL,
    GITLAB_MODE_HOSTED,
    GITLAB_MODE_KEY,
    GITLAB_MODES,
    OMNIA_ENV_FILE,
)

_MODE_CACHE: Dict[str, Dict[str, Any]] = {}
_CONNECTION_CACHE: Dict[str, Dict[str, Any]] = {}


def reset_gitlab_mode_cache() -> None:
    """Forget the resolved mode and connection (the next call reads the OIM again)."""
    _MODE_CACHE.clear()
    _CONNECTION_CACHE.clear()


def read_vault_mapping(host: Any, input_dir: str) -> Dict[str, Any]:
    """Decrypt build_stream_credentials.yml with its vault key on the OIM.

    The values are secrets: callers keep them in this process and never log,
    print or report them.

    Raises:
        RuntimeError: When the store cannot be decrypted or is not a mapping.
    """
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


def resolve_gitlab_mode(host: Any, refresh: bool = False) -> Dict[str, Any]:
    """Read ``gitlab_mode`` from the build_stream input file on the OIM (cached).

    Returns:
        Dict with keys: success (the mode is ``hosted`` or ``external``), mode
        ("" when unreadable or unsupported), config (parsed input file), path
        (input file), error.
    """
    if not refresh and "result" in _MODE_CACHE:
        return _MODE_CACHE["result"]
    result: Dict[str, Any] = {"success": False, "mode": "", "config": {}, "path": "",
                              "error": ""}
    try:
        path = f"{domain_input_path(host, BSM_DOMAIN)}/{BSM_CONFIG_FILE}"
        result["path"] = path
        config = read_remote_yaml(host, path) or {}
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        result["error"] = f"Cannot read {result['path'] or BSM_CONFIG_FILE}: {exc}"
        return result
    mode = gitlab_mode_of(config)
    result.update(config=config, mode=mode if mode in GITLAB_MODES else "")
    if mode in GITLAB_MODES:
        result["success"] = True
        _MODE_CACHE["result"] = result
    else:
        result["error"] = (
            f"{GITLAB_MODE_KEY} in {path} must be one of {', '.join(GITLAB_MODES)} "
            f"(found {mode or 'nothing'})"
        )
    return result


def mode_applies(host: Any, required: str) -> Dict[str, Any]:
    """Decide whether a test written for ``required`` mode applies to this run.

    A mode that cannot be resolved never skips a test: the test then runs and
    reports the problem itself.

    Returns:
        Dict with keys: applies, mode, reason (set when applies is False).
    """
    resolved = resolve_gitlab_mode(host)
    if not resolved["success"] or resolved["mode"] == required:
        return {"applies": True, "mode": resolved["mode"], "reason": ""}
    return {
        "applies": False,
        "mode": resolved["mode"],
        "reason": (
            f"{GITLAB_MODE_KEY} is '{resolved['mode']}' in {resolved['path']}; "
            f"this test verifies {required} mode only"
        ),
    }


def external_tls(host: Any, ca_path: str) -> ssl.SSLContext:
    """Return a TLS context that verifies the external GitLab.

    ``ca_path`` is a PEM bundle on the OIM (``gitlab_ca_cert_path``); an empty
    value uses the system trust store, as the product does.

    Raises:
        RuntimeError: When the bundle cannot be read or is not a certificate.
    """
    if not ca_path:
        return ssl.create_default_context()
    result = run_cmd(host, "cat_file", path=ca_path)
    if result.rc != 0:
        raise RuntimeError(f"GitLab CA bundle {ca_path} not readable (rc={result.rc})")
    try:
        return tls_from_pem(result.stdout)
    except ssl.SSLError as exc:
        raise RuntimeError(f"GitLab CA bundle {ca_path} is invalid: {exc}") from exc


def _external_input_problem(resolved: Dict[str, Any]) -> str:
    """Return why the resolved input file cannot be used for external mode ("" = usable)."""
    if not resolved["success"]:
        return resolved["error"]
    if resolved["mode"] != GITLAB_MODE_EXTERNAL:
        return f"{GITLAB_MODE_KEY} is '{resolved['mode']}', not external"
    settings = external_settings(resolved["config"])
    if settings["url"] and settings["namespace"]:
        return ""
    return (f"{GITLAB_EXTERNAL_CONFIG_KEYS['url']} and "
            f"{GITLAB_EXTERNAL_CONFIG_KEYS['namespace']} must be set in {resolved['path']}")


def external_connection(host: Any) -> Dict[str, Any]:
    """Resolve the external GitLab API endpoint, token, TLS and project.

    Returns:
        Dict with keys: success, error and, on success, config, input_dir,
        settings (see ``external_settings``), url, api (``<url>/api/v4``),
        headers (token header), tls, project_ref (URL-encoded project path),
        project_id (from the credential store, "" when not persisted yet).
    """
    if "result" in _CONNECTION_CACHE:
        return _CONNECTION_CACHE["result"]
    resolved = resolve_gitlab_mode(host)
    problem = _external_input_problem(resolved)
    if problem:
        return {"success": False, "error": problem}
    settings = external_settings(resolved["config"])
    try:
        input_dir = domain_input_path(host, BSM_DOMAIN)
        credentials = read_vault_mapping(host, input_dir)
        tls = external_tls(host, settings["ca_path"])
    except (RuntimeError, ValueError, yaml.YAMLError) as exc:
        return {"success": False, "error": str(exc)}
    token = str(credentials.get(GITLAB_EXTERNAL_TOKEN_KEY) or "")
    if not token:
        return {"success": False,
                "error": f"{GITLAB_EXTERNAL_TOKEN_KEY} is empty in {BSM_CREDENTIALS_FILE}"}
    connection = {
        "success": True,
        "error": "",
        "config": resolved["config"],
        "input_dir": input_dir,
        "settings": settings,
        "url": settings["url"],
        "api": f"{settings['url']}{GITLAB_API}",
        "headers": {"PRIVATE-TOKEN": token},
        "tls": tls,
        "project_ref": urllib.parse.quote(settings["project_path"], safe=""),
        "project_id": str(credentials.get(GITLAB_EXTERNAL_PROJECT_ID_KEY) or ""),
    }
    _CONNECTION_CACHE["result"] = connection
    return connection


def check_gitlab_mode_inputs(host: Any, expected_mode: str = "") -> Dict[str, Any]:
    """Resolve ``gitlab_mode`` from the input file and validate the inputs it needs.

    Args:
        host: Testinfra host connection.
        expected_mode: ``hosted`` or ``external`` to assert the input file
            selects that mode ("" = accept either).

    Returns:
        Dict with keys: name, success, fields, failures, error, mode.
    """
    resolved = resolve_gitlab_mode(host, refresh=True)
    probes = [("Input file", resolved["path"] or "unknown", bool(resolved["path"]))]
    if resolved["success"]:
        probes.extend(mode_input_probes(resolved["mode"], resolved["config"], expected_mode))
    else:
        probes.append(("gitlab_mode", resolved["error"], False))
    result = summarize_probes("gitlab_mode", probes)
    result["mode"] = resolved["mode"]
    return result


__all__ = [
    "check_gitlab_mode_inputs",
    "external_connection",
    "external_settings",
    "external_tls",
    "gitlab_mode_of",
    "mode_applies",
    "read_vault_mapping",
    "reset_gitlab_mode_cache",
    "resolve_gitlab_mode",
    "GITLAB_MODE_EXTERNAL",
    "GITLAB_MODE_HOSTED",
]
