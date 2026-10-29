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

"""Domain credential store helper used by setup_env.sh.

Domain stores written by the playbooks hold nested data (build_stream
``oauth_clients``, repo_manager ``registry_credentials``) that the flat
omnia_auto credential CLI refuses to load. This helper decrypts with the
Ansible Vault API, updates only the top-level fields named in a spec,
keeps every other key, and re-encrypts atomically (0600). Secrets are read
from the terminal or stdin, never from arguments, and are never printed.

Commands::

    status      exit 0 when every required spec field is a non-empty string
    prompt      prompt for the spec fields (Enter keeps a stored value)
    write-stdin merge a JSON object from stdin (spec fields only)
    hash-auth   store the Argon2id hash of build_stream_auth_password
"""

import argparse
import getpass
import json
import os
import secrets
import sys
import tempfile
from typing import Any, Dict, List

import yaml
from ansible.parsing.vault import VaultLib, VaultSecret

KEY_LENGTH = 32


def _vault(key_path: str, create: bool = False) -> VaultLib:
    """Return a VaultLib for the key file, creating a 0600 key when allowed."""
    if not os.path.exists(key_path):
        if not create:
            raise SystemExit(f"Vault key not found: {key_path}")
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(secrets.token_urlsafe(KEY_LENGTH)[:KEY_LENGTH] + "\n")
    with open(key_path, "rb") as stream:
        return VaultLib([("default", VaultSecret(stream.read().strip()))])


def _load(path: str, key_path: str) -> Dict[str, Any]:
    """Decrypt (or read) a credential store; a missing or empty file is empty."""
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as stream:
        raw = stream.read()
    if not raw.strip():
        return {}
    text = _vault(key_path).decrypt(raw) if raw.startswith(b"$ANSIBLE_VAULT") else raw
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"{path} is not a mapping")
    return data


def _save(path: str, key_path: str, data: Dict[str, Any]) -> None:
    """Encrypt ``data`` and replace the store atomically with mode 0600."""
    payload = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
    encrypted = _vault(key_path, create=True).encrypt(payload.encode("utf-8"))
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".credentials.", dir=directory)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encrypted)
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _is_set(value: Any) -> bool:
    """Return whether a field holds a non-empty scalar value."""
    return isinstance(value, (str, int)) and not isinstance(value, bool) and bool(
        str(value).strip())


def _missing(spec: List[Dict[str, Any]], data: Dict[str, Any]) -> List[str]:
    """Return the required spec fields that are not set in ``data``."""
    return [item["field"] for item in spec
            if not item.get("optional") and not _is_set(data.get(item["field"]))]


def _check(item: Dict[str, Any], value: str) -> str:
    """Return a validation error for ``value`` (empty when valid)."""
    minimum = int(item.get("min_length", 1 if not item.get("optional") else 0))
    if value and len(value) < minimum:
        return f"{item['label']} must be at least {minimum} characters"
    return ""


def _prompt(spec: List[Dict[str, Any]], data: Dict[str, Any]) -> None:
    """Prompt on the terminal for each spec field; Enter keeps a stored value."""
    group = None
    with open("/dev/tty", "r", encoding="utf-8") as tty:
        for item in spec:
            if item.get("group") and item["group"] != group:
                group = item["group"]
                print(f"\n  {group}")
            stored = _is_set(data.get(item["field"]))
            hint = " [stored, Enter keeps]" if stored else (
                " (optional, Enter skips)" if item.get("optional") else "")
            while True:
                label = f"    {item['label']}{hint}: "
                if item.get("secret"):
                    value = getpass.getpass(label)
                else:
                    print(label, end="", flush=True)
                    value = tty.readline().strip()
                if not value:
                    if stored or item.get("optional"):
                        break
                    print("    A value is required.")
                    continue
                error = _check(item, value)
                if error:
                    print(f"    {error}")
                    continue
                if item.get("secret") and item.get("confirm") and (
                        getpass.getpass(f"    Confirm {item['label']}: ") != value):
                    print("    Values do not match.")
                    continue
                data[item["field"]] = value
                break


def main() -> int:
    """Run one helper command."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("status", "prompt", "write-stdin", "hash-auth"))
    parser.add_argument("--creds-path", required=True)
    parser.add_argument("--key-path", required=True)
    parser.add_argument("--spec", default="[]", help="JSON field specification")
    args = parser.parse_args()
    spec = json.loads(args.spec)

    try:
        data = _load(args.creds_path, args.key_path)
    except (SystemExit, Exception) as exc:  # pylint: disable=broad-except
        if args.command == "status":
            return 1
        raise SystemExit(f"Cannot read {args.creds_path}: {exc}") from exc

    if args.command == "status":
        return 1 if _missing(spec, data) else 0

    if args.command == "hash-auth":
        from argon2 import PasswordHasher, Type  # pylint: disable=import-outside-toplevel
        _bsa_key = "build_stream_auth"
        raw_value = str(data.get(f"{_bsa_key}_password") or "")
        if not raw_value:
            raise SystemExit(f"{_bsa_key}_password is not set")
        data[f"{_bsa_key}_password_hash"] = PasswordHasher(
            time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16,
            type=Type.ID).hash(raw_value)
    elif args.command == "prompt":
        _prompt(spec, data)
    else:
        supplied = json.load(sys.stdin)
        if not isinstance(supplied, dict):
            raise SystemExit("Credential JSON must be an object")
        allowed = {item["field"]: item for item in spec}
        unknown = sorted(set(supplied) - set(allowed))
        if unknown:
            raise SystemExit(f"Unsupported fields: {', '.join(unknown)}")
        for field, value in supplied.items():
            if not isinstance(value, str):
                raise SystemExit(f"{field} must be a string")
            error = _check(allowed[field], value)
            if error:
                raise SystemExit(error)
            data[field] = value

    missing = _missing(spec, data)
    if missing:
        raise SystemExit(f"Required fields missing: {', '.join(missing)}")
    _save(args.creds_path, args.key_path, data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
