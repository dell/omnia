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


"""Read the domain credential stores from OpenBao (KV v1 or v2) for ./setup_env.sh.

``./setup_env.sh --domain-creds-from-openbao`` (or ``--openbao`` with no action) reads
``<server_url>/v1/<secret_path>/<domain>`` for each domain, the same layout the
GitLab pipelines use (secret/data/omnia/repo_manager ...), and gives the fields
to the suite's ``--domain-creds-stdin``. Only the standard library is used.

Secrets: the token comes from BAO_TOKEN or a prompt, never from a file or an argument;
values are returned in memory only, and only field NAMES are ever printed.
"""

import getpass
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List

from ..vars.common_vars import OPENBAO_TOKEN_ENV

Emit = Callable[[str], None]
TIMEOUT_SECONDS = 30
MAX_BYTES = 1024 * 1024


class OpenBaoError(RuntimeError):
    """The credentials could not be read; the message says why and how to fix it."""


def token(prompt: bool = True) -> str:
    """Return the OpenBao token: BAO_TOKEN, else a hidden prompt on a terminal.

    Raises:
        OpenBaoError: No token and no terminal to ask on.
    """
    value = os.environ.get(OPENBAO_TOKEN_ENV, "").strip()
    if value:
        return value
    if prompt and sys.stdin.isatty():
        value = getpass.getpass("OpenBao token (not shown, not logged): ").strip()
    if not value:
        raise OpenBaoError(f"no OpenBao token. HOW TO FIX: export {OPENBAO_TOKEN_ENV}=<token> "
                           "(a token that may read the secret path), or run on a terminal")
    return value


def _context(settings: Dict[str, Any], emit: Emit) -> ssl.SSLContext:
    """Return the TLS context: unchecked, a given CA file, or the system store."""
    if settings["tls_skip_verify"]:
        emit("WARNING: openbao.tls_skip_verify is true: the OpenBao certificate is not "
             "checked (set openbao.ca_cert instead)")
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    if settings["ca_cert"]:
        if not os.path.isfile(settings["ca_cert"]):
            raise OpenBaoError(f"openbao.ca_cert {settings['ca_cert']} is not a file")
        return ssl.create_default_context(cafile=settings["ca_cert"])
    return ssl.create_default_context()


def _get(url: str, bao_token: str, context: ssl.SSLContext) -> Dict[str, Any]:
    """GET ``url`` with the token; return the JSON body. Errors never include the body."""
    request = urllib.request.Request(url, headers={"X-Vault-Token": bao_token})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS,  # nosec B310  # https URL from the checked config
                                    context=context) as response:
            body = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        why = {403: "permission denied (the token may not read this path)",
               404: "not found (check openbao.secret_path and the domain name)"}.get(
                   exc.code, f"HTTP {exc.code}")
        raise OpenBaoError(why) from exc
    except (urllib.error.URLError, OSError, ssl.SSLError) as exc:
        reason = getattr(exc, "reason", exc)
        raise OpenBaoError(f"cannot reach OpenBao: {type(reason).__name__}: {reason}") from exc
    if len(body) > MAX_BYTES:
        raise OpenBaoError("the OpenBao answer is too large")
    try:
        data = json.loads(body)
    except ValueError as exc:
        raise OpenBaoError("the OpenBao answer is not JSON") from exc
    return data if isinstance(data, dict) else {}


def fields_of(answer: Dict[str, Any]) -> Dict[str, str]:
    """Return the string fields of a KV v1 or v2 answer (no metadata, no empty values)."""
    data = answer.get("data")
    data = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), dict) \
        else data
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()
            if key != "metadata" and value is not None and str(value) != ""}


def read_domains(settings: Dict[str, Any], domains: List[str], bao_token: str,
                 emit: Emit) -> Dict[str, Dict[str, str]]:
    """Return {domain: {field: value}} for ``domains`` from OpenBao.

    Raises:
        OpenBaoError: The settings are incomplete, OpenBao cannot be reached or a domain has
            no secret.
    """
    if not settings["server_url"] or not settings["secret_path"]:
        raise OpenBaoError("openbao.server_url and openbao.secret_path are not set. HOW TO "
                           "FIX: fill the openbao block of build_stream_test_config.yml")
    context = _context(settings, emit)
    found: Dict[str, Dict[str, str]] = {}
    for domain in domains:
        url = f"{settings['server_url']}/v1/{settings['secret_path']}/{domain}"
        try:
            fields = fields_of(_get(url, bao_token, context))
        except OpenBaoError as exc:
            raise OpenBaoError(f"{domain}: {exc} ({settings['secret_path']}/{domain})") from exc
        if not fields:
            raise OpenBaoError(f"{domain}: the secret {settings['secret_path']}/{domain} has no "
                               "fields")
        emit(f"  {domain:<20} {len(fields)} fields: {', '.join(sorted(fields))}")
        found[domain] = fields
    return found
