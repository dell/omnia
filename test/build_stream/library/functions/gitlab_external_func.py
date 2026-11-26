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

"""Verification of an external (customer-managed) GitLab configured by Omnia.

Each ``check_*`` function verifies what ``build_stream.yml --tags execute``
leaves on an external GitLab when ``gitlab_mode: external`` (ER-BSM-003):
validated inputs, CA bundle, GitLab version and token, the Omnia project, the
online runner, the ``omnia-ci`` project access token, the trigger, the CI/CD
variables and the setup journal.

Every check only reads state, over the GitLab REST API with verified TLS.
Secrets (the personal access token, variable values) stay in this process;
only names, flags and counts are reported.
"""

import json
import re
import urllib.parse
from typing import Any, Dict, List

from library.functions.probe_func import Probe, domain_output_path, summarize_probes
from library.gitlab_external_helpers import days_until, gitlab_major_version, mode_is_ca_safe

from .execute_probe_func import data_path, domain_input_path, run_cmd
from .gitlab_mode_func import (
    external_connection,
    external_settings,
    read_vault_mapping,
    resolve_gitlab_mode,
)
from .http_func import http_json
from ..vars.execute_vars import (
    BSM_CONFIG_KEYS,
    BSM_DOMAIN,
    BSM_TLS_CERT,
    EXTERNAL_CI_TOKEN_ACCESS_LEVEL,
    EXTERNAL_CI_TOKEN_MAX_DAYS,
    EXTERNAL_CI_TOKEN_NAME,
    EXTERNAL_CI_TOKEN_SCOPE,
    EXTERNAL_CI_VARIABLES,
    EXTERNAL_JOURNAL_FILE,
    EXTERNAL_JOURNAL_RESOURCE_TYPES,
    EXTERNAL_JOURNAL_SCHEMA_VERSION,
    EXTERNAL_MIN_NAMESPACE_ACCESS_LEVEL,
    EXTERNAL_PRIVATE_FILE_MODES,
    EXTERNAL_PROJECT_MARKER,
    EXTERNAL_REQUIRED_SCOPES,
    EXTERNAL_SUPPORTED_MAJOR_VERSIONS,
    EXTERNAL_TRIGGER_DESCRIPTION,
    EXTERNAL_TRIGGER_TOKEN_FILE,
    GITLAB_EXTERNAL_CONFIG_KEYS,
    GITLAB_EXTERNAL_PROJECT_ID_KEY,
    GITLAB_EXTERNAL_TOKEN_KEY,
    GITLAB_PEM_CERT_MARKER,
    GITLAB_PEM_KEY_MARKER,
    GITLAB_TOKEN_SELF_PATH,
    GITLAB_USER_PATH,
    GITLAB_VERSION_PATH,
)

# Token shapes GitLab issues (personal, runner, pipeline trigger / project access tokens).
_TOKEN_RE = re.compile(r"\b(glpat|glrt|glptt|gldt)-[A-Za-z0-9_-]{10,}")
_PAGE = "per_page=100"


def _api_get(connection: Dict[str, Any], path: str) -> Dict[str, Any]:
    """GET a GitLab API path (relative to ``/api/v4``) with the verified connection."""
    return http_json(connection["tls"], "GET", f"{connection['api']}{path}",
                     headers=connection["headers"])


def _stat(host: Any, path: str) -> Dict[str, str]:
    """Return the owner uid and octal mode of an OIM file ({} when it cannot be read)."""
    result = run_cmd(host, "stat_owner_mode", path=path)
    owner, _, mode = result.stdout.strip().partition("|")
    return {"owner": owner, "mode": mode} if result.rc == 0 and mode else {}


def _failed(name: str, label: str, error: str) -> Dict[str, Any]:
    """Return a failed result with one crossed item."""
    return summarize_probes(name, [(label, error, False)])


def _connection(host: Any, name: str):
    """Return (connection, None) or (None, failed result) for the external GitLab."""
    connection = external_connection(host)
    if not connection["success"]:
        return None, _failed(name, "External GitLab connection", connection["error"])
    return connection, None


def _project(connection: Dict[str, Any]) -> Dict[str, Any]:
    """Return the Omnia project from the API ({} when it cannot be read)."""
    response = _api_get(connection, f"/projects/{connection['project_ref']}")
    data = response["data"] if response["success"] else {}
    return data if isinstance(data, dict) else {}


def _journal(host: Any) -> Dict[str, Any]:
    """Return the setup journal text and parsed content ({} values when unreadable)."""
    path = f"{domain_output_path(host, 'build_stream')}/{EXTERNAL_JOURNAL_FILE}"
    result = run_cmd(host, "cat_file", path=path)
    parsed: Dict[str, Any] = {}
    if result.rc == 0:
        try:
            loaded = json.loads(result.stdout)
            parsed = loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            parsed = {}
    return {"path": path, "text": result.stdout if result.rc == 0 else "", "data": parsed,
            "rc": result.rc}


# =============================================================================
# EXTERNAL MODE CHECKS
# =============================================================================

def check_external_credentials(host: Any) -> Dict[str, Any]:
    """Verify the credential store holds what the external mode needs.

    ``gitlab_api_token`` must be set (the value is never reported) and the
    execute step must have persisted ``gitlab_project_id``. No hosted-only
    secret (``gitlab_root_password``, ``gitlab_ssh_password``) is required.
    """
    resolved = resolve_gitlab_mode(host)
    if not resolved["success"]:
        return _failed("external_credentials", "gitlab_mode", resolved["error"])
    try:
        credentials = read_vault_mapping(host, domain_input_path(host, BSM_DOMAIN))
    except (RuntimeError, ValueError) as exc:
        return _failed("external_credentials", "Credential store", str(exc))
    token = str(credentials.get(GITLAB_EXTERNAL_TOKEN_KEY) or "")
    project_id = str(credentials.get(GITLAB_EXTERNAL_PROJECT_ID_KEY) or "")
    probes: List[Probe] = [
        (GITLAB_EXTERNAL_TOKEN_KEY, "set" if token else "EMPTY", bool(token)),
        (GITLAB_EXTERNAL_PROJECT_ID_KEY, project_id or "NOT PERSISTED", project_id.isdigit()),
    ]
    return summarize_probes("external_credentials", probes)


def check_external_ca_bundle(host: Any) -> Dict[str, Any]:
    """Verify ``gitlab_ca_cert_path``: PEM certificates only, root-owned, mode 0644 or stricter.

    An empty value is valid: Omnia then uses the system trust store, which the
    API checks of this suite also use.
    """
    resolved = resolve_gitlab_mode(host)
    if not resolved["success"]:
        return _failed("external_ca_bundle", "gitlab_mode", resolved["error"])
    ca_path = external_settings(resolved["config"])["ca_path"]
    if not ca_path:
        return summarize_probes("external_ca_bundle", [
            (GITLAB_EXTERNAL_CONFIG_KEYS["ca"], "not set (system trust store)", True)])
    content = run_cmd(host, "cat_file", path=ca_path)
    probes: List[Probe] = [(f"File {ca_path}", "readable" if content.rc == 0 else "NOT READABLE",
                            content.rc == 0)]
    if content.rc == 0:
        text = content.stdout
        probes.append(("PEM certificate", "present" if GITLAB_PEM_CERT_MARKER in text
                       else "NO CERTIFICATE BLOCK", GITLAB_PEM_CERT_MARKER in text))
        probes.append(("Private key", "none" if GITLAB_PEM_KEY_MARKER not in text
                       else "PRIVATE KEY IN BUNDLE", GITLAB_PEM_KEY_MARKER not in text))
        stat = _stat(host, ca_path)
        probes.append(("Owner", "root" if stat.get("owner") == "0"
                       else f"uid {stat.get('owner', 'unknown')}", stat.get("owner") == "0"))
        mode = stat.get("mode", "")
        probes.append(("Mode", mode or "unknown", mode_is_ca_safe(mode)))
    return summarize_probes("external_ca_bundle", probes)


def check_external_gitlab_api(host: Any, min_token_days: int = 0) -> Dict[str, Any]:
    """Verify the external GitLab version, token scopes and expiry, and group role.

    Args:
        host: Testinfra host connection.
        min_token_days: Fail when the token expires in fewer days (0 = only an
            expired token fails).
    """
    connection, failure = _connection(host, "external_gitlab_api")
    if failure:
        return failure
    probes: List[Probe] = [("TLS", f"verified, {connection['url']}", True)]
    version = _api_get(connection, GITLAB_VERSION_PATH)
    text = str((version["data"] or {}).get("version", "")) if version["success"] else ""
    major = gitlab_major_version(text)
    supported = ", ".join(f"{item}.x" for item in EXTERNAL_SUPPORTED_MAJOR_VERSIONS)
    probes.append(("GitLab version", text or version["error"],
                   major in EXTERNAL_SUPPORTED_MAJOR_VERSIONS))
    if major not in EXTERNAL_SUPPORTED_MAJOR_VERSIONS:
        probes.append(("Supported versions", supported, False))
    token = _api_get(connection, GITLAB_TOKEN_SELF_PATH)
    token_data = token["data"] if token["success"] and isinstance(token["data"], dict) else {}
    scopes = sorted(token_data.get("scopes", []))
    missing = [scope for scope in EXTERNAL_REQUIRED_SCOPES if scope not in scopes]
    probes.append(("Token scopes", ", ".join(scopes) or token["error"] or "none", not missing))
    remaining = days_until(token_data.get("expires_at") or "")
    if remaining is None:
        probes.append(("Token expiry", "no expiry date", token["success"]))
    else:
        probes.append(("Token expiry", f"{remaining} days left",
                       remaining >= 0 and remaining >= min_token_days))
    active = bool(token_data) and not token_data.get("revoked")
    probes.append(("Token active", "yes" if active else "REVOKED OR UNREADABLE", active))
    probes.append(_namespace_role(connection))
    return summarize_probes("external_gitlab_api", probes)


def _namespace_role(connection: Dict[str, Any]) -> Probe:
    """Probe: the token user is an administrator or Owner/Maintainer of the group."""
    namespace = connection["settings"]["namespace"]
    user = _api_get(connection, GITLAB_USER_PATH)
    user_data = user["data"] if user["success"] and isinstance(user["data"], dict) else {}
    group = _api_get(connection, f"/groups/{urllib.parse.quote(namespace, safe='')}")
    group_data = group["data"] if group["success"] and isinstance(group["data"], dict) else {}
    label = f"Role on group {namespace}"
    if not user_data.get("id"):
        return label, f"TOKEN USER NOT READABLE ({user['error'] or 'no user'})", False
    if not group_data.get("id"):
        return label, "GROUP NOT FOUND OR NOT VISIBLE", False
    if user_data.get("is_admin"):
        return label, f"administrator ({user_data.get('username', '')})", True
    member = _api_get(connection, f"/groups/{group_data['id']}/members/all/{user_data.get('id')}")
    level = int((member["data"] or {}).get("access_level", 0)) if member["success"] else 0
    return label, f"access level {level}", level >= EXTERNAL_MIN_NAMESPACE_ACCESS_LEVEL


def check_external_project(host: Any) -> Dict[str, Any]:
    """Verify the Omnia project: namespace, ownership marker, visibility, protected branch."""
    connection, failure = _connection(host, "external_project")
    if failure:
        return failure
    settings = connection["settings"]
    project = _project(connection)
    if not project.get("id"):
        return _failed("external_project", f"Project {settings['project_path']}",
                       "NOT FOUND on the external GitLab")
    probes: List[Probe] = [
        ("Project path", str(project.get("path_with_namespace")),
         project.get("path_with_namespace") == settings["project_path"]),
        ("Ownership marker", EXTERNAL_PROJECT_MARKER if EXTERNAL_PROJECT_MARKER
         in str(project.get("description") or "") else "MISSING",
         EXTERNAL_PROJECT_MARKER in str(project.get("description") or "")),
        ("Visibility", f"{project.get('visibility')} (expected {settings['visibility']})",
         project.get("visibility") == settings["visibility"]),
        ("Default branch", f"{project.get('default_branch')} (expected {settings['branch']})",
         project.get("default_branch") == settings["branch"]),
    ]
    branch = urllib.parse.quote(settings["branch"], safe="")
    protected = _api_get(connection, f"/projects/{project['id']}/protected_branches/{branch}")
    probes.append((f"Protected branch {settings['branch']}",
                   "protected" if protected["success"] else "NOT PROTECTED", protected["success"]))
    persisted = connection["project_id"]
    probes.append(("Project ID in credential store",
                   f"{persisted or 'NOT PERSISTED'} (project {project['id']})",
                   persisted == str(project["id"])))
    return summarize_probes("external_project", probes)


def check_external_runner(host: Any) -> Dict[str, Any]:
    """Verify an operator-provided runner is online and Omnia recorded it as user_provided."""
    connection, failure = _connection(host, "external_runner")
    if failure:
        return failure
    project = _project(connection)
    if not project.get("id"):
        return _failed("external_runner", "Project", "NOT FOUND on the external GitLab")
    runners = _api_get(connection, f"/projects/{project['id']}/runners?status=online&{_PAGE}")
    online = runners["data"] if runners["success"] and isinstance(runners["data"], list) else []
    names = ", ".join(str(item.get("description") or item.get("id")) for item in online)
    probes: List[Probe] = [("Online runners", f"{len(online)} ({names})" if online
                            else runners["error"] or "NONE ONLINE", bool(online))]
    journal = _journal(host)
    entries = [item for item in journal["data"].get("resources", [])
               if isinstance(item, dict) and item.get("type") == "runner"]
    actions = {str(item.get("action")) for item in entries}
    probes.append(("Journal runner entry", ", ".join(sorted(actions)) or "NONE",
                   actions == {"user_provided"}))
    return summarize_probes("external_runner", probes)


def check_external_ci_token(host: Any) -> Dict[str, Any]:
    """Verify the ``omnia-ci`` project access token (api scope, Maintainer, <= 360 days)."""
    connection, failure = _connection(host, "external_ci_token")
    if failure:
        return failure
    project = _project(connection)
    if not project.get("id"):
        return _failed("external_ci_token", "Project", "NOT FOUND on the external GitLab")
    listed = _api_get(connection, f"/projects/{project['id']}/access_tokens?state=active&{_PAGE}")
    tokens = [item for item in (listed["data"] if listed["success"] else []) or []
              if isinstance(item, dict) and item.get("name") == EXTERNAL_CI_TOKEN_NAME]
    probes: List[Probe] = [(f"Active {EXTERNAL_CI_TOKEN_NAME} tokens", str(len(tokens)),
                            len(tokens) == 1)]
    if tokens:
        token = tokens[0]
        probes.append(("Scopes", ", ".join(token.get("scopes", [])),
                       EXTERNAL_CI_TOKEN_SCOPE in token.get("scopes", [])))
        probes.append(("Access level", str(token.get("access_level")),
                       token.get("access_level") == EXTERNAL_CI_TOKEN_ACCESS_LEVEL))
        remaining = days_until(token.get("expires_at") or "")
        probes.append(("Expiry", "unknown" if remaining is None else f"{remaining} days left",
                       remaining is not None and 0 < remaining <= EXTERNAL_CI_TOKEN_MAX_DAYS + 1))
        recorded = [str(item.get("token_id")) for item in _journal(host)["data"].get(
            "resources", []) if isinstance(item, dict) and item.get("type") == "access_token"]
        probes.append(("Token ID in journal", ", ".join(recorded) or "NONE",
                       str(token.get("id")) in recorded))
    return summarize_probes("external_ci_token", probes)


def check_external_trigger_and_variables(host: Any) -> Dict[str, Any]:
    """Verify the pipeline trigger, its local token file and the CI/CD variables.

    Variable values are compared only when they are not secrets: ``BSM_API_URL``
    and ``BSM_API_CERT`` (the public BuildStream certificate). Masked and
    protected flags are verified for every variable.
    """
    connection, failure = _connection(host, "external_trigger_variables")
    if failure:
        return failure
    project = _project(connection)
    if not project.get("id"):
        return _failed("external_trigger_variables", "Project", "NOT FOUND on the external GitLab")
    base = f"/projects/{project['id']}"
    probes: List[Probe] = []
    triggers = _api_get(connection, f"{base}/triggers")
    found = [item for item in (triggers["data"] if triggers["success"] else []) or []
             if isinstance(item, dict) and item.get("description") == EXTERNAL_TRIGGER_DESCRIPTION]
    probes.append((f"Trigger '{EXTERNAL_TRIGGER_DESCRIPTION}'", "present" if found else "MISSING",
                   bool(found)))
    token_file = f"{domain_output_path(host, 'build_stream')}/{EXTERNAL_TRIGGER_TOKEN_FILE}"
    stat = _stat(host, token_file)
    private = stat.get("owner") == "0" and stat.get("mode") in EXTERNAL_PRIVATE_FILE_MODES
    probes.append((f"File {token_file}", f"owner {stat.get('owner', 'unknown')} mode "
                   f"{stat.get('mode', 'unknown')}", private))
    probes.extend(_variable_probes(host, connection, base))
    return summarize_probes("external_trigger_variables", probes)


def _variable_probes(host: Any, connection: Dict[str, Any], base: str) -> List[Probe]:
    """Probes for the Omnia-managed CI/CD variables and the non-secret values."""
    listed = _api_get(connection, f"{base}/variables?{_PAGE}")
    variables = {item.get("key"): item for item in (listed["data"] if listed["success"] else [])
                 or [] if isinstance(item, dict)}
    probes: List[Probe] = []
    for key, (masked, protected) in EXTERNAL_CI_VARIABLES.items():
        item = variables.get(key)
        if item is None:
            probes.append((f"Variable {key}", "MISSING", False))
            continue
        ok = bool(item.get("masked")) == masked and bool(item.get("protected")) == protected
        probes.append((f"Variable {key}", f"masked={bool(item.get('masked'))} "
                       f"protected={bool(item.get('protected'))}", ok))
    probes.extend(_value_probes(host, connection, variables))
    return probes


def _value_probes(host: Any, connection: Dict[str, Any],
                  variables: Dict[str, Dict[str, Any]]) -> List[Probe]:
    """Probes for the non-secret variable values and the CA path."""
    config = connection["config"]
    api_host, api_port = (config.get(BSM_CONFIG_KEYS[key]) for key in ("api_host", "api_port"))
    expected_url = f"https://{api_host}:{api_port}" if api_host and api_port else ""
    url_value = (variables.get("BSM_API_URL") or {}).get("value")
    cert = run_cmd(host, "cat_file", path=f"{data_path(host)}/{BSM_TLS_CERT}")
    cert_value = str((variables.get("BSM_API_CERT") or {}).get("value") or "")
    same_cert = cert.rc == 0 and cert_value.strip() == cert.stdout.strip()
    ca_path = connection["settings"]["ca_path"]
    leaked = bool(ca_path) and any(ca_path in str(item.get("value") or "")
                                   for item in variables.values())
    return [
        ("BSM_API_URL value", f"{url_value} (expected {expected_url or 'api host/port unset'})",
         bool(expected_url) and url_value == expected_url),
        ("BSM_API_CERT equals bs_cert.pem",
         "equal" if same_cert else "DIFFERENT OR UNREADABLE", same_cert),
        ("CA path injected into CI/CD variables", "YES" if leaked else "no", not leaked),
    ]


def _journal_secret_probe(host: Any, connection: Dict[str, Any], text: str) -> Probe:
    """Probe: the journal holds no token (the PAT, the trigger token or any GitLab token shape)."""
    secrets = [connection["headers"]["PRIVATE-TOKEN"]]
    trigger = run_cmd(host, "cat_file", path=f"{domain_output_path(host, 'build_stream')}/"
                                             f"{EXTERNAL_TRIGGER_TOKEN_FILE}")
    if trigger.rc == 0 and trigger.stdout.strip():
        secrets.append(trigger.stdout.strip())
    found = [name for name, hit in (
        ("personal access token", secrets[0] in text),
        ("trigger token", len(secrets) > 1 and secrets[1] in text),
        ("token-shaped value", bool(_TOKEN_RE.search(text))),
    ) if hit]
    return ("Secret values in journal", ", ".join(found).upper() if found else "none", not found)


def check_external_journal(host: Any) -> Dict[str, Any]:
    """Verify the setup journal: private file, schema, project, resource types, no secrets."""
    connection, failure = _connection(host, "external_journal")
    if failure:
        return failure
    journal = _journal(host)
    if journal["rc"] != 0 or not journal["data"]:
        return _failed("external_journal", f"File {journal['path']}", "MISSING OR NOT JSON")
    data = journal["data"]
    stat = _stat(host, journal["path"])
    types = {str(item.get("type")) for item in data.get("resources", [])
             if isinstance(item, dict)}
    missing = [name for name in EXTERNAL_JOURNAL_RESOURCE_TYPES if name not in types]
    probes: List[Probe] = [
        (f"File {journal['path']}", f"owner {stat.get('owner', 'unknown')} mode "
         f"{stat.get('mode', 'unknown')}",
         stat.get("owner") == "0" and stat.get("mode") in EXTERNAL_PRIVATE_FILE_MODES),
        ("Schema version", str(data.get("schema_version")),
         data.get("schema_version") == EXTERNAL_JOURNAL_SCHEMA_VERSION),
        ("GitLab URL", str(data.get("gitlab_url")), data.get("gitlab_url") == connection["url"]),
        ("Project ID", f"{data.get('project_id')} (credential store {connection['project_id']})",
         str(data.get("project_id")) == connection["project_id"]),
        ("Resource types", ", ".join(sorted(types)) or "NONE", not missing),
    ]
    if missing:
        probes.append(("Missing resource types", ", ".join(missing), False))
    probes.append(_journal_secret_probe(host, connection, journal["text"]))
    return summarize_probes("external_journal", probes)


# =============================================================================
# EXTERNAL MODE CLEANUP CHECKS
# =============================================================================
# What build_stream.yml --tags cleanup removes on an external GitLab
# (gitlab_mode: external): the Omnia-owned project named in build_stream_config.yml
# (deleted outright, taking its CI files, catalogs, input files, CI/CD variables,
# the omnia-ci token and the trigger with it), while the pre-existing
# group/namespace and any GitLab CE packages/runner/certs are NEVER touched. The
# local setup journal, its lock and the trigger token file are removed from the
# OIM. Every check only reads state over the GitLab REST API with verified TLS.


def _cleanup_api_or_local(host: Any, name: str):
    """Return (connection, None), or (None, result) when the API cannot be used.

    After cleanup with ``cleanup_credentials: true`` the ``gitlab_api_token`` is
    blanked in the credential store, so the remote GitLab can no longer be
    queried. Blanking credentials is local evidence, not evidence of remote
    state, so the check is returned as ``skipped`` (unverified) instead of
    passed; the caller must skip the test rather than report a pass.
    """
    connection = external_connection(host)
    if connection["success"]:
        return connection, None
    if "is empty" in connection.get("error", ""):
        reason = ("gitlab_api_token was removed from the credential store "
                  "(cleanup_credentials: true); remote GitLab state cannot be verified")
        result = summarize_probes(name, [("Remote GitLab state", f"UNVERIFIED ({reason})", True)])
        result.update(skipped=True, skip_reason=reason)
        return None, result
    return None, _failed(name, "External GitLab connection", connection["error"])


def check_external_project_removed(host: Any) -> Dict[str, Any]:
    """Verify the Omnia-owned project was permanently deleted from the external GitLab."""
    connection, result = _cleanup_api_or_local(host, "external_cleanup_project_removed")
    if result is not None:
        return result
    settings = connection["settings"]
    response = _api_get(connection, f"/projects/{connection['project_ref']}")
    status = response.get("status", 0)
    data = response["data"] if isinstance(response.get("data"), dict) else {}
    marked = bool(data.get("marked_for_deletion_on") or data.get("marked_for_deletion_at"))
    if status == 404:
        state = "permanently deleted (HTTP 404)"
    elif status == 200 and marked:
        deletion_date = data.get("marked_for_deletion_on") or data.get("marked_for_deletion_at")
        state = f"STILL PRESENT (scheduled for deletion on {deletion_date})"
    else:
        state = f"STILL PRESENT (HTTP {status})"
    probes: List[Probe] = [
        (f"Omnia project {settings['project_path']}", state, status == 404),
    ]
    return summarize_probes("external_cleanup_project_removed", probes)


def check_external_namespace_preserved(host: Any) -> Dict[str, Any]:
    """Verify the pre-existing group/namespace was NOT removed by the cleanup."""
    connection, result = _cleanup_api_or_local(host, "external_cleanup_namespace_preserved")
    if result is not None:
        return result
    namespace = connection["settings"]["namespace"]
    group = _api_get(connection, f"/groups/{urllib.parse.quote(namespace, safe='')}")
    present = group["success"] and isinstance(group["data"], dict) and bool(group["data"].get("id"))
    probes: List[Probe] = [
        (f"Group/namespace {namespace}",
         "preserved" if present else f"MISSING ({group['error'] or 'not found'})", present),
    ]
    return summarize_probes("external_cleanup_namespace_preserved", probes)


def check_external_ci_resources_removed(host: Any) -> Dict[str, Any]:
    """Verify the omnia-ci token, the Omnia trigger and the Omnia CI/CD variables are gone.

    When the project was deleted they are removed with it; when an adopted
    project is preserved they must be gone from it one by one.
    """
    connection, result = _cleanup_api_or_local(host, "external_cleanup_ci_resources_removed")
    if result is not None:
        return result
    project = _project(connection)
    marked = bool(project.get("marked_for_deletion_on") or project.get("marked_for_deletion_at"))
    if not project.get("id"):
        return summarize_probes("external_cleanup_ci_resources_removed", [(
            "Omnia project resources",
            "project permanently deleted; omnia-ci token, trigger and CI/CD variables removed with it",
            True)])
    if marked:
        return summarize_probes("external_cleanup_ci_resources_removed", [(
            "Omnia project resources",
            "project STILL PRESENT and only scheduled for deletion",
            False)])
    base = f"/projects/{project['id']}"
    tokens = _api_get(connection, f"{base}/access_tokens?state=active&{_PAGE}")
    omnia_tokens = [item for item in (tokens["data"] if tokens["success"] else []) or []
                    if isinstance(item, dict) and item.get("name") == EXTERNAL_CI_TOKEN_NAME]
    triggers = _api_get(connection, f"{base}/triggers")
    omnia_triggers = [item for item in (triggers["data"] if triggers["success"] else []) or []
                      if isinstance(item, dict)
                      and item.get("description") == EXTERNAL_TRIGGER_DESCRIPTION]
    variables = _api_get(connection, f"{base}/variables?{_PAGE}")
    omnia_vars = [item.get("key") for item in (variables["data"] if variables["success"] else [])
                  or [] if isinstance(item, dict) and item.get("key") in EXTERNAL_CI_VARIABLES]
    probes: List[Probe] = [
        (f"Active {EXTERNAL_CI_TOKEN_NAME} tokens", str(len(omnia_tokens)), not omnia_tokens),
        (f"Omnia trigger '{EXTERNAL_TRIGGER_DESCRIPTION}'",
         "removed" if not omnia_triggers else f"{len(omnia_triggers)} STILL PRESENT",
         not omnia_triggers),
        ("Omnia CI/CD variables",
         "removed" if not omnia_vars else f"STILL PRESENT ({', '.join(omnia_vars)})",
         not omnia_vars),
    ]
    return summarize_probes("external_cleanup_ci_resources_removed", probes)


def check_external_cleanup_local_state_removed(host: Any) -> Dict[str, Any]:
    """Verify the setup journal, its lock and the trigger token file are removed on the OIM."""
    output_dir = domain_output_path(host, "build_stream")
    paths = [
        f"{output_dir}/{EXTERNAL_JOURNAL_FILE}",
        f"{output_dir}/{EXTERNAL_JOURNAL_FILE}.lock",
        f"{output_dir}/{EXTERNAL_TRIGGER_TOKEN_FILE}",
    ]
    probes: List[Probe] = []
    for path in paths:
        present = run_cmd(host, "file_exists", path=path).rc == 0
        probes.append((f"File {path}", "STILL PRESENT" if present else "removed", not present))
    return summarize_probes("external_cleanup_local_state_removed", probes)


__all__ = [
    "check_external_ca_bundle",
    "check_external_ci_resources_removed",
    "check_external_ci_token",
    "check_external_cleanup_local_state_removed",
    "check_external_credentials",
    "check_external_gitlab_api",
    "check_external_journal",
    "check_external_namespace_preserved",
    "check_external_project",
    "check_external_project_removed",
    "check_external_runner",
    "check_external_trigger_and_variables",
]
