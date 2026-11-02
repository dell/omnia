#!/usr/bin/env python3
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

"""Fetch one OpenBao KV v2 secret with the GitLab job id_token (JWT login).

    python3 ci/scripts/bao_fetch.py --cluster <cluster> --secret <name> \
        (--json | --field <key>) --out <file>

Connection settings come from clusters/<cluster>/cluster.yml. The JWT is read
from the SVT_ID_TOKEN job variable (GitLab id_tokens), never from arguments.
The secret is written to --out with mode 0600 and never printed; TLS is
always verified (openbao_cacert or the system trust store).
Exit codes: 0 written, 2 usage/config, 3 the field is absent, 4 OpenBao error.
"""

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from svt_ci import NAME_RE, TAG_RE, ConfigError, load_cluster

JWT_ENV = "SVT_ID_TOKEN"
TIMEOUT = 30


class BaoError(Exception):
    """OpenBao refused or failed a request (message holds no secret)."""


def _context(cacert: str) -> ssl.SSLContext:
    return ssl.create_default_context(cafile=cacert or None)


def _request(context: ssl.SSLContext, method: str, url: str,
             token: Optional[str] = None, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Vault-Token"] = token
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, context=context, timeout=TIMEOUT) as response:  # nosec B310
            return json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        raise BaoError(f"{method} {url.split('/v1/', 1)[-1]}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise BaoError(f"{method} {url.split('/v1/', 1)[-1]}: {exc}") from exc


def fetch(cluster: Dict[str, Any], secret: str) -> Dict[str, Any]:
    """Log in with the job JWT and return the secret's key/value data."""
    jwt = os.environ.get(JWT_ENV, "")
    if not jwt:
        raise BaoError(f"{JWT_ENV} is not set: the job needs id_tokens.{JWT_ENV}")
    base = str(cluster["openbao_addr"]).rstrip("/")
    context = _context(cluster["openbao_cacert"])
    login = _request(context, "POST", f"{base}/v1/auth/{cluster['openbao_auth_mount']}/login",
                     body={"role": cluster["openbao_role"], "jwt": jwt})
    token = (login.get("auth") or {}).get("client_token")
    if not token:
        raise BaoError("JWT login returned no client token")
    path = f"{cluster['openbao_kv_mount']}/data/{cluster['openbao_path']}/{secret}"
    data = ((_request(context, "GET", f"{base}/v1/{path}", token=token).get("data") or {})
            .get("data") or {})
    if not isinstance(data, dict) or not data:
        raise BaoError(f"secret {cluster['openbao_path']}/{secret} is empty or missing")
    return data


def write_private(path: str, text: str) -> None:
    """Create ``path`` with mode 0600 and write ``text``."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(text)


def main(argv) -> int:
    """Parse the arguments, fetch and write the secret."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--secret", required=True, help="oim or a module name")
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--json", action="store_true", help="write every field as JSON")
    output.add_argument("--field", help="write one field as text")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        cluster = load_cluster(args.cluster)
        if not TAG_RE.fullmatch(args.secret) or (args.field and not NAME_RE.fullmatch(args.field)):
            raise ConfigError("invalid --secret or --field name")
        data = fetch(cluster, args.secret)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except BaoError as exc:
        print(f"ERROR: OpenBao: {exc}", file=sys.stderr)
        return 4
    if args.field:
        value = data.get(args.field)
        if not value:
            return 3
        write_private(args.out, str(value) if str(value).endswith("\n") else f"{value}\n")
    else:
        write_private(args.out, json.dumps(data))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
