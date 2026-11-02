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

"""Store the SVT secrets of one cluster in OpenBao (KV version 2).

    ./openbao_secrets.py --addr https://bao:8200 --cluster cluster1 [--module all]
    ./openbao_secrets.py --print-setup --gitlab-url https://gitlab --project root/omnia-svt

Secrets live at <kv-mount>/<path>/<module> (default secret/omnia/<cluster>):
  oim                   ssh_private_key (from a key file, recommended) or password
  repo_manager | image_build_manager | orchestrator | build_stream
                        the product credential fields (same names as the
                        domain credential files, see test/build_stream/setup_env.sh)
Values are asked with hidden prompts (or read once as JSON from --values-stdin);
the OpenBao token is asked hidden too (or read from a 0600 --token-file). Nothing
secret is printed, logged or passed as an argument. TLS is always verified.
"""

import argparse
import getpass
import json
import os
import re
import ssl
import stat
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

MODULE_FIELDS: Dict[str, List[Dict[str, Any]]] = {
    "repo_manager": [
        {"field": "pulp_password", "secret": True},
        {"field": "docker_username", "secret": False, "optional": True},
        {"field": "docker_password", "secret": True, "optional": True},
    ],
    "image_build_manager": [
        {"field": "s3_access_id", "secret": False, "optional": True},
        {"field": "s3_secret_key", "secret": True},
        {"field": "aarch64_ssh_password", "secret": True, "optional": True},
    ],
    "orchestrator": [
        {"field": "provision_password", "secret": True},
        {"field": "bmc_username", "secret": False},
        {"field": "bmc_password", "secret": True},
        {"field": "slurm_db_password", "secret": True, "optional": True},
        {"field": "openldap_db_username", "secret": False, "optional": True},
        {"field": "openldap_db_password", "secret": True, "optional": True},
        {"field": "csi_username", "secret": False, "optional": True},
        {"field": "csi_password", "secret": True, "optional": True},
    ],
    "build_stream": [
        {"field": "gitlab_root_password", "secret": True},
        {"field": "gitlab_ssh_password", "secret": True},
        {"field": "build_stream_auth_username", "secret": False},
        {"field": "build_stream_auth_password", "secret": True},
        {"field": "postgres_user", "secret": False},
        {"field": "postgres_password", "secret": True},
    ],
}
MODULES = ["oim", *MODULE_FIELDS]
CLUSTER_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}")
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}")
MAX_STDIN_BYTES = 65536
TIMEOUT = 30

SETUP_TEMPLATE = """# --- OpenBao one-time setup for the SVT project (run as an OpenBao admin) ---
bao secrets enable -path={kv} -version=2 kv 2>/dev/null || true
bao auth enable jwt 2>/dev/null || true
bao write auth/jwt/config oidc_discovery_url="{gitlab}" bound_issuer="{gitlab}"
bao policy write {role} - <<'POLICY'
path "{kv}/data/omnia/*" {{ capabilities = ["read"] }}
POLICY
bao write auth/jwt/role/{role} role_type=jwt user_claim=user_email \\
    bound_audiences="<openbao_addr from cluster.yml>" bound_claims_type=glob \\
    bound_claims='{{"project_path":"{project}","ref_protected":"true","ref_type":"branch"}}' \\
    token_policies={role} token_ttl=1h token_max_ttl=2h
"""


class SecretError(Exception):
    """Input or OpenBao failure (the message holds no secret)."""


def _read_private_file(path: str) -> str:
    """Read a file that only its owner may read (mode 0600 or stricter)."""
    info = os.stat(path)
    if info.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise SecretError(f"{path} must not be readable by group or others (chmod 600)")
    with open(path, "r", encoding="utf-8") as stream:
        return stream.read().strip()


def _ask(field: str, secret: bool, optional: bool) -> str:
    label = f"{field}{' (optional, Enter to skip)' if optional else ''}: "
    while True:
        value = getpass.getpass(label) if secret else input(label).strip()
        if secret and value and getpass.getpass(f"confirm {field}: ") != value:
            print("  values differ, try again")
            continue
        if value or optional:
            return value
        print("  a value is required")


def collect(module: str, provided: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Return the fields of a module from --values-stdin or prompts."""
    if module == "oim":
        if provided is not None:
            data = {key: str(provided[key]) for key in ("ssh_private_key", "password")
                    if provided.get(key)}
        else:
            key_path = input("OIM SSH private key file (Enter to use a password instead): ").strip()
            data = ({"ssh_private_key": _read_private_file(key_path) + "\n"} if key_path
                    else {"password": _ask("password", True, False)})
        if not data:
            raise SecretError("oim needs ssh_private_key or password")
        return data
    fields = MODULE_FIELDS[module]
    if provided is not None:
        unknown = set(provided) - {item["field"] for item in fields}
        if unknown:
            raise SecretError(f"{module}: unknown field(s) {', '.join(sorted(unknown))}")
        data = {item["field"]: str(provided.get(item["field"]) or "") for item in fields}
    else:
        print(f"--- {module}")
        data = {item["field"]: _ask(item["field"], item["secret"], item.get("optional", False))
                for item in fields}
    missing = [item["field"] for item in fields if not item.get("optional") and not data[item["field"]]]
    if missing:
        raise SecretError(f"{module}: required field(s) empty: {', '.join(missing)}")
    return {key: value for key, value in data.items() if value}


def write_secret(addr: str, token: str, cacert: Optional[str], path: str,
                 data: Dict[str, str]) -> None:
    """Write one KV v2 secret."""
    request = urllib.request.Request(
        f"{addr.rstrip('/')}/v1/{path}", method="POST",
        data=json.dumps({"data": data}).encode(),
        headers={"X-Vault-Token": token, "Content-Type": "application/json"})
    context = ssl.create_default_context(cafile=cacert or None)
    try:
        with urllib.request.urlopen(request, context=context, timeout=TIMEOUT):  # nosec B310
            pass
    except urllib.error.HTTPError as exc:
        raise SecretError(f"write {path}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise SecretError(f"write {path}: {exc}") from exc


def main(argv: List[str]) -> int:
    """Parse the arguments and store the secrets."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("--addr", help="https://<openbao>:8200")
    parser.add_argument("--cluster", help="cluster folder name")
    parser.add_argument("--module", choices=[*MODULES, "all"], default="all")
    parser.add_argument("--kv-mount", default="secret")
    parser.add_argument("--path", help="secret path (default omnia/<cluster>)")
    parser.add_argument("--cacert", help="CA file of the OpenBao certificate")
    parser.add_argument("--token-file", help="0600 file holding the OpenBao token")
    parser.add_argument("--values-stdin", action="store_true",
                        help='read {"<module>": {"<field>": "<value>"}} JSON from stdin')
    parser.add_argument("--print-setup", action="store_true",
                        help="print the one-time OpenBao JWT/policy commands and exit")
    parser.add_argument("--gitlab-url", help="with --print-setup")
    parser.add_argument("--project", help="with --print-setup: namespace/name")
    parser.add_argument("--role", default="omnia-svt")
    args = parser.parse_args(argv)
    try:
        if args.print_setup:
            if not (args.gitlab_url and args.project):
                raise SecretError("--print-setup needs --gitlab-url and --project")
            print(SETUP_TEMPLATE.format(kv=args.kv_mount, gitlab=args.gitlab_url.rstrip("/"),
                                        role=args.role, project=args.project))
            return 0
        if not (args.addr or "").startswith("https://"):
            raise SecretError("--addr must be an https:// URL")
        if not CLUSTER_RE.fullmatch(args.cluster or ""):
            raise SecretError("--cluster must be the cluster folder name")
        base = args.path or f"omnia/{args.cluster}"
        if not NAME_RE.fullmatch(base) or not NAME_RE.fullmatch(args.kv_mount):
            raise SecretError("invalid --path or --kv-mount")
        provided = None
        if args.values_stdin:
            raw = sys.stdin.read(MAX_STDIN_BYTES + 1)
            if len(raw) > MAX_STDIN_BYTES:
                raise SecretError("stdin payload too large")
            provided = json.loads(raw)
            if not isinstance(provided, dict):
                raise SecretError("stdin must be a JSON object")
        token = (_read_private_file(args.token_file) if args.token_file
                 else getpass.getpass("OpenBao token: "))
        if not token:
            raise SecretError("the OpenBao token is empty")
        for module in (MODULES if args.module == "all" else [args.module]):
            values = None if provided is None else provided.get(module, {})
            data = collect(module, values)
            write_secret(args.addr, token, args.cacert, f"{args.kv_mount}/data/{base}/{module}", data)
            print(f"stored {args.kv_mount}/{base}/{module} ({len(data)} field(s))")
    except (SecretError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
