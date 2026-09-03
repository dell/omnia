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
Credential management for omnia test automation.

Provides vault key creation, credential encryption / decryption,
field reading / writing, and interactive prompting.

All file paths are derived from environment variables set by
``omnia.env`` (``OMNIA_DATA_PATH``, ``OMNIA_PROJECT_NAME``).

Usage from Python::

    from omnia_auto.functions.credential_func import (
        ensure_vault_key,
        write_credential_fields,
        read_credential_field,
    )

Usage from bash (CLI mode)::

    python -m omnia_auto.functions.credential_func ensure-key \\
        --key-path /opt/omnia/telemetry/input/project_default/.telemetry_credentials_key

    python -m omnia_auto.functions.credential_func write-fields \\
        --creds-path /opt/omnia/telemetry/input/project_default/telemetry_credentials.yml \\
        --key-path /opt/omnia/telemetry/input/project_default/.telemetry_credentials_key \\
        --fields '{"bmc_username": "admin", "bmc_password": "<value>"}'
"""

import argparse
import getpass
import json
import os
import secrets
import subprocess
import sys
from typing import Any, Dict

import yaml

from ..vars.credential_vars import (
    VAULT_FILE_MODE,
    VAULT_HEADER,
    VAULT_KEY_LENGTH,
    VAULT_TIMEOUT,
)
from ..messages.credential_msgs import (
    CREDENTIAL_LOG_MSGS as LOG,
    CREDENTIAL_ERROR_MSGS as ERR,
)
from .process_security import (
    atomic_sensitive_output,
    descriptor_path,
    open_sensitive_text,
    protect_sensitive_file as _protect_sensitive_file,
    scrubbed_subprocess_environment,
    sensitive_file_descriptor,
    temporary_sensitive_descriptor,
)


def _run_vault_encrypt(
    plaintext_fd: int, key_fd: int, encrypted_fd: int,
) -> None:
    """Encrypt descriptor content and validate the resulting Vault payload."""
    inherited_fds = (plaintext_fd, key_fd, encrypted_fd)
    subprocess.run(
        [
            "ansible-vault",
            "encrypt",
            descriptor_path(plaintext_fd),
            "--output",
            descriptor_path(encrypted_fd),
            "--vault-password-file",
            descriptor_path(key_fd),
        ],
        capture_output=True,
        text=True,
        timeout=VAULT_TIMEOUT,
        check=True,
        pass_fds=inherited_fds,
        env=scrubbed_subprocess_environment(),
    )
    header = os.pread(
        encrypted_fd, len(VAULT_HEADER), 0,
    ).decode("ascii", errors="replace")
    if header != VAULT_HEADER:
        raise ValueError("ansible-vault did not produce encrypted output")


# =====================================================================
# VAULT KEY MANAGEMENT
# =====================================================================

def ensure_vault_key(key_path: str) -> Dict[str, Any]:
    """Create a vault key file if it does not already exist.

    Args:
        key_path: Absolute path to the vault key file.

    Returns:
        Dict with keys: created (bool), message (str).
    """
    if os.path.lexists(key_path):
        _protect_sensitive_file(key_path)
        return {
            "created": False,
            "message": LOG["vault_key_exists"].format(key_path=key_path),
        }
    token = secrets.token_urlsafe(VAULT_KEY_LENGTH)[:VAULT_KEY_LENGTH]
    parent = os.path.dirname(key_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
    )
    key_fd = os.open(key_path, flags, VAULT_FILE_MODE)
    try:
        os.fchmod(key_fd, VAULT_FILE_MODE)
    except OSError:
        os.close(key_fd)
        raise
    with os.fdopen(key_fd, "w", encoding="utf-8") as key_fh:
        key_fh.write(token)
    return {
        "created": True,
        "message": LOG["vault_key_created"].format(key_path=key_path),
    }


# =====================================================================
# VAULT ENCRYPTION / DECRYPTION
# =====================================================================

def is_vault_encrypted(creds_path: str) -> bool:
    """Check whether a file is ansible-vault encrypted.

    Args:
        creds_path: Path to the credentials file.

    Returns:
        True if the first line starts with ``$ANSIBLE_VAULT``.
    """
    if not os.path.lexists(creds_path):
        return False
    with open_sensitive_text(
        creds_path, VAULT_FILE_MODE,
    ) as creds_fh:
        first_line = creds_fh.readline().strip()
    return first_line.startswith(VAULT_HEADER)


def vault_encrypt(creds_path: str, key_path: str) -> Dict[str, Any]:
    """Encrypt a credentials file with ansible-vault.

    Args:
        creds_path: Path to the plaintext credentials YAML.
        key_path: Path to the vault key file.

    Returns:
        Dict with keys: success (bool), message (str), error (str).
    """
    try:
        if is_vault_encrypted(creds_path):
            return {
                "success": True,
                "message": LOG["creds_already_encrypted"].format(
                    creds_path=creds_path,
                ),
                "error": "",
            }

        with sensitive_file_descriptor(
            creds_path, VAULT_FILE_MODE,
        ) as creds_fd, sensitive_file_descriptor(
            key_path, VAULT_FILE_MODE,
        ) as key_fd, atomic_sensitive_output(
            creds_path, VAULT_FILE_MODE,
        ) as encrypted_fd:
            _run_vault_encrypt(creds_fd, key_fd, encrypted_fd)

        return {
            "success": True,
            "message": LOG["creds_encrypted"].format(
                creds_path=creds_path,
            ),
            "error": "",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": "",
            "error": ERR["vault_not_installed"],
        }
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        error_text = getattr(exc, "stderr", "") or str(exc)
        return {
            "success": False,
            "message": "",
            "error": ERR["encrypt_failed"].format(
                creds_path=creds_path,
                key_path=key_path,
                error=error_text.strip(),
            ),
        }
    except (OSError, ValueError) as exc:
        return {
            "success": False,
            "message": "",
            "error": ERR["encrypt_failed"].format(
                creds_path=creds_path,
                key_path=key_path,
                error=str(exc),
            ),
        }


def vault_decrypt_to_dict(
    creds_path: str, key_path: str,
) -> Dict[str, Any]:
    """Decrypt an ansible-vault file and return contents as a dict.

    Args:
        creds_path: Path to the encrypted credentials file.
        key_path: Path to the vault key file.

    Returns:
        Dict with keys: success (bool), data (dict), error (str).
    """
    if not os.path.lexists(creds_path):
        return {
            "success": False,
            "data": {},
            "error": ERR["creds_not_found"].format(
                creds_path=creds_path,
            ),
        }
    if not os.path.lexists(key_path):
        return {
            "success": False,
            "data": {},
            "error": ERR["key_not_found"].format(
                key_path=key_path, creds_path=creds_path,
            ),
        }
    try:
        with sensitive_file_descriptor(
            creds_path, VAULT_FILE_MODE,
        ) as creds_fd, sensitive_file_descriptor(
            key_path, VAULT_FILE_MODE,
        ) as key_fd:
            inherited_fds = (creds_fd, key_fd)
            result = subprocess.run(
                [
                    "ansible-vault",
                    "view",
                    descriptor_path(creds_fd),
                    "--vault-password-file",
                    descriptor_path(key_fd),
                ],
                capture_output=True,
                text=True,
                timeout=VAULT_TIMEOUT,
                check=True,
                pass_fds=inherited_fds,
                env=scrubbed_subprocess_environment(),
            )
        data = yaml.safe_load(result.stdout) or {}
        return {"success": True, "data": data, "error": ""}
    except FileNotFoundError:
        return {
            "success": False,
            "data": {},
            "error": ERR["vault_not_installed"],
        }
    except (
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as exc:
        error_text = getattr(exc, "stderr", "") or str(exc)
        return {
            "success": False,
            "data": {},
            "error": ERR["decrypt_failed"].format(
                creds_path=creds_path,
                key_path=key_path,
                error=error_text.strip(),
            ),
        }


# =====================================================================
# FIELD OPERATIONS
# =====================================================================

def read_credential_field(
    creds_path: str,
    key_path: str,
    field: str,
) -> Dict[str, Any]:
    """Read a single field from a (possibly encrypted) credentials file.

    Args:
        creds_path: Path to the credentials file.
        key_path: Path to the vault key file.
        field: YAML key to read.

    Returns:
        Dict with keys: success (bool), value (str or None), error (str).
    """
    if not os.path.exists(creds_path):
        return {
            "success": False,
            "value": None,
            "error": ERR["creds_not_found"].format(
                creds_path=creds_path,
            ),
        }

    if is_vault_encrypted(creds_path):
        result = vault_decrypt_to_dict(creds_path, key_path)
        if not result["success"]:
            return {
                "success": False,
                "value": None,
                "error": result["error"],
            }
        data = result["data"]
    else:
        with open_sensitive_text(
            creds_path, VAULT_FILE_MODE,
        ) as creds_fh:
            data = yaml.safe_load(creds_fh) or {}

    value = data.get(field)
    if value is not None:
        return {"success": True, "value": str(value), "error": ""}
    return {
        "success": False,
        "value": None,
        "error": LOG["field_not_found"].format(
            field=field, creds_path=creds_path,
        ),
    }


def write_credential_fields(
    creds_path: str,
    key_path: str,
    fields: Dict[str, str],
    header_comment: str = "",
) -> Dict[str, Any]:
    """Write / update fields in a credentials file and encrypt it.

    Existing fields not in *fields* are preserved.  New fields are
    merged.  The file is encrypted after writing.

    Args:
        creds_path: Path to the credentials file.
        key_path: Path to the vault key file.
        fields: Dict of field_name -> value to write.
        header_comment: Optional comment block for the file header.

    Returns:
        Dict with keys: success (bool), message (str), error (str).
    """
    existing: Dict = {}
    if os.path.exists(creds_path):
        if is_vault_encrypted(creds_path):
            result = vault_decrypt_to_dict(creds_path, key_path)
            if not result["success"]:
                return {
                    "success": False,
                    "message": "",
                    "error": result["error"],
                }
            existing = result["data"]
        else:
            with open_sensitive_text(
                creds_path, VAULT_FILE_MODE,
            ) as creds_fh:
                existing = yaml.safe_load(creds_fh) or {}

    existing.update(fields)

    ensure_vault_key(key_path)

    parent = os.path.dirname(creds_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    try:
        with temporary_sensitive_descriptor(
            parent or None, VAULT_FILE_MODE,
        ) as plaintext_fd:
            with os.fdopen(
                os.dup(plaintext_fd), "w", encoding="utf-8",
            ) as creds_fh:
                if header_comment:
                    for line in header_comment.strip().splitlines():
                        creds_fh.write(f"# {line}\n")
                    creds_fh.write("\n")
                yaml.safe_dump(
                    existing, creds_fh,
                    default_flow_style=False, allow_unicode=True,
                )
            os.lseek(plaintext_fd, 0, os.SEEK_SET)

            with sensitive_file_descriptor(
                key_path, VAULT_FILE_MODE,
            ) as key_fd, atomic_sensitive_output(
                creds_path, VAULT_FILE_MODE,
            ) as encrypted_fd:
                _run_vault_encrypt(plaintext_fd, key_fd, encrypted_fd)
    except FileNotFoundError:
        return {
            "success": False,
            "message": "",
            "error": ERR["vault_not_installed"],
        }
    except (
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as exc:
        error_text = getattr(exc, "stderr", "") or str(exc)
        return {
            "success": False,
            "message": "",
            "error": ERR["encrypt_failed"].format(
                creds_path=creds_path,
                key_path=key_path,
                error=error_text.strip(),
            ),
        }

    return {
        "success": True,
        "message": LOG["creds_written"].format(creds_path=creds_path),
        "error": "",
    }


def prompt_credential(
    message: str = "Enter secret",  # noqa: S107 — prompt label, not a credential
) -> str:
    """Prompt the user for a secret value (no echo).

    Args:
        message: Prompt text.

    Returns:
        The entered value.
    """
    return getpass.getpass(prompt=f"  {message}: ")


def prompt_and_confirm(
    message: str = "Credential",
) -> str:
    """Prompt for a secret twice and confirm both entries match.

    Loops until the user provides a non-empty value that matches
    on both entries.  All output goes to stderr so that the secret
    is returned cleanly on stdout for shell capture.

    Args:
        message: Prompt label (e.g. ``Credential``).

    Returns:
        The confirmed secret value.
    """
    while True:
        first = getpass.getpass(prompt=f"  {message}: ")
        if not first:
            print(
                "  ERROR: Value cannot be empty. Try again.\n",
                file=sys.stderr, flush=True,
            )
            continue
        second = getpass.getpass(prompt=f"  Confirm {message}: ")
        if first == second:
            return first
        print(
            "  ERROR: Values do not match. Try again.\n",
            file=sys.stderr, flush=True,
        )


def _read_visible_input(prompt_text: str) -> str:
    """Read one visible terminal line without using Python's ``input``."""
    sys.stdout.write(prompt_text)
    sys.stdout.flush()
    value = sys.stdin.readline()
    if value == "":
        raise EOFError("EOF when reading a line")
    return value.rstrip("\r\n")


def prompt_fields_interactive(
    field_spec: list,
    existing: Dict[str, str] = None,
) -> Dict[str, str]:
    """Prompt interactively for multiple credential fields.

    Each field spec is a dict with keys:
        - field: YAML field name (required)
        - label: Display label (optional, defaults to field)
        - group: Group header to print before this field (optional)
        - secret: If True, read with getpass (no echo) (default True)
        - confirm: If True and secret, prompt twice and verify match (default False)
        - optional: If True, allow empty value (default False)

    Args:
        field_spec: List of field specification dicts.
        existing: Dict of existing values to show as defaults.

    Returns:
        Dict of field_name -> entered_value (only non-empty values).

    Example::

        fields = prompt_fields_interactive([
            {"field": "bmc_username", "label": "BMC Username", "group": "iDRAC BMC"},
            {"field": "bmc_password", "label": "BMC Password", "secret": True, "confirm": True},
        ])
    """
    if not isinstance(field_spec, list):
        raise ValueError("Credential field specification must be a list")
    if existing is None:
        existing = {}
    if not isinstance(existing, dict):
        raise ValueError("Existing credential values must be a mapping")

    result = {}
    current_group = None

    for spec in field_spec:
        if not isinstance(spec, dict):
            raise ValueError("Each credential field specification must be a mapping")
        field_name = spec.get("field")
        if not isinstance(field_name, str) or not field_name:
            continue

        label = spec.get("label", field_name)
        group = spec.get("group")
        is_secret = spec.get("secret", True)
        is_optional = spec.get("optional", False)
        needs_confirm = spec.get("confirm", False) and is_secret

        # Print group header if changed
        if group and group != current_group:
            print(f"\n  \033[1;33m{group}:\033[0m", file=sys.stderr, flush=True)
            current_group = group

        # Get existing value
        existing_val = existing.get(field_name, "")

        if is_secret:
            if existing_val:
                prompt_text = f"  {label} [set]: "
            else:
                prompt_text = f"  {label}: "
            entered = getpass.getpass(prompt=prompt_text)

            # Confirm if requested and value was entered
            if needs_confirm and entered:
                confirm_text = f"  Confirm {label}: "
                confirmed = getpass.getpass(prompt=confirm_text)
                if entered != confirmed:
                    print(
                        f"  \033[0;31m[ERROR]\033[0m {label} entries do not match!",
                        file=sys.stderr, flush=True,
                    )
                    raise ValueError(f"{label} confirmation failed")
        else:
            if existing_val:
                prompt_text = f"  {label} [{existing_val}]: "
            else:
                prompt_text = f"  {label}: "
            entered = _read_visible_input(prompt_text)

        # Use entered value or fall back to existing
        final_value = entered if entered else existing_val

        # Store if non-empty (or always store if optional allows empty)
        if final_value or is_optional:
            result[field_name] = final_value

    return result


def read_all_fields(
    creds_path: str,
    key_path: str,
) -> Dict[str, Any]:
    """Read all fields from a (possibly encrypted) credentials file.

    Args:
        creds_path: Path to the credentials file.
        key_path: Path to the vault key file.

    Returns:
        Dict with keys: success (bool), data (dict), error (str).
    """
    if not os.path.exists(creds_path):
        return {"success": True, "data": {}, "error": ""}

    if is_vault_encrypted(creds_path):
        return vault_decrypt_to_dict(creds_path, key_path)

    try:
        with open_sensitive_text(
            creds_path, VAULT_FILE_MODE,
        ) as creds_fh:
            data = yaml.safe_load(creds_fh) or {}
        return {"success": True, "data": data, "error": ""}
    except Exception as exc:
        return {"success": False, "data": {}, "error": str(exc)}


# =====================================================================
# CLI ENTRY POINT
# =====================================================================

_CLI_COMMANDS = frozenset({
    "ensure-key", "encrypt", "read-field", "read-all",
    "write-fields", "prompt", "prompt-and-confirm",
    "prompt-fields", "is-encrypted",
})


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the credential CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m omnia_auto.functions.credential_func",
        description="Credential management for omnia test automation.",
    )
    sub = parser.add_subparsers(dest="command")

    # ensure-key
    ek = sub.add_parser(
        "ensure-key", help="Create vault key if missing.",
    )
    ek.add_argument("--key-path", required=True)

    # encrypt
    enc = sub.add_parser(
        "encrypt", help="Encrypt a credentials file.",
    )
    enc.add_argument("--creds-path", required=True)
    enc.add_argument("--key-path", required=True)

    # read-field
    rf = sub.add_parser(
        "read-field",
        help="Read one field from credentials.",
    )
    rf.add_argument("--creds-path", required=True)
    rf.add_argument("--key-path", required=True)
    rf.add_argument("--field", required=True)

    # write-fields
    wf = sub.add_parser(
        "write-fields",
        help="Write / merge fields and encrypt.",
    )
    wf.add_argument("--creds-path", required=True)
    wf.add_argument("--key-path", required=True)
    wf.add_argument(
        "--fields", required=True,
        help='JSON string: {"field": "value", ...}',
    )
    wf.add_argument("--header", default="")

    # prompt
    pr = sub.add_parser(
        "prompt", help="Prompt for a secret (no echo).",
    )
    pr.add_argument(
        "--message", default="Enter secret",  # noqa: S107
    )

    # prompt-and-confirm
    pac = sub.add_parser(
        "prompt-and-confirm",
        help="Prompt for secret with confirmation (2x entry).",
    )
    pac.add_argument(
        "--message", default="Credential",
        help="Prompt label (default: Credential).",
    )

    # is-encrypted
    ie = sub.add_parser(
        "is-encrypted",
        help="Check if vault-encrypted (exit 0=yes, 1=no).",
    )
    ie.add_argument("--creds-path", required=True)

    # read-all
    ra = sub.add_parser(
        "read-all",
        help="Read all fields from credentials as JSON.",
    )
    ra.add_argument("--creds-path", required=True)
    ra.add_argument("--key-path", required=True)

    # prompt-fields
    pf = sub.add_parser(
        "prompt-fields",
        help="Interactive prompt for multiple fields, write to file.",
    )
    pf.add_argument("--creds-path", required=True)
    pf.add_argument("--key-path", required=True)
    pf.add_argument(
        "--spec", required=True,
        help='JSON array: [{"field":"x","label":"X","group":"G","secret":true}]',
    )

    return parser


def main(argv=None) -> int:
    """CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 = success).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "ensure-key":
        result = ensure_vault_key(args.key_path)
        status = "CREATED" if result["created"] else "EXISTS"
        print(status, flush=True)

    elif args.command == "encrypt":
        ensure_vault_key(args.key_path)
        result = vault_encrypt(args.creds_path, args.key_path)
        if not result["success"]:
            print(
                f"ERROR: {result['error']}",
                file=sys.stderr, flush=True,
            )
            return 2
        print("ENCRYPTED", flush=True)

    elif args.command == "read-field":
        result = read_credential_field(
            args.creds_path, args.key_path, args.field,
        )
        if result["success"]:
            print(result["value"], flush=True)
        else:
            print(
                f"ERROR: {result['error']}",
                file=sys.stderr, flush=True,
            )
            return 1

    elif args.command == "write-fields":
        fields = json.loads(args.fields)
        result = write_credential_fields(
            args.creds_path, args.key_path,
            fields, header_comment=args.header,
        )
        if result["success"]:
            print("OK", flush=True)
        else:
            print(
                f"ERROR: {result['error']}",
                file=sys.stderr, flush=True,
            )
            return 2

    elif args.command == "prompt":
        secret = prompt_credential(args.message)
        print(secret, flush=True)

    elif args.command == "prompt-and-confirm":
        secret = prompt_and_confirm(args.message)
        print(secret, flush=True)

    elif args.command == "is-encrypted":
        if is_vault_encrypted(args.creds_path):
            print("YES", flush=True)
            return 0
        print("NO", flush=True)
        return 1

    elif args.command == "read-all":
        result = read_all_fields(args.creds_path, args.key_path)
        if result["success"]:
            print(json.dumps(result["data"]), flush=True)
        else:
            print(
                f"ERROR: {result['error']}",
                file=sys.stderr, flush=True,
            )
            return 1

    elif args.command == "prompt-fields":
        # Parse field spec
        field_spec = json.loads(args.spec)

        # Read existing values
        existing_result = read_all_fields(args.creds_path, args.key_path)
        existing = existing_result.get("data", {})

        # Prompt for fields
        entered = prompt_fields_interactive(field_spec, existing)

        # Write to file
        if entered:
            result = write_credential_fields(
                args.creds_path, args.key_path, entered,
            )
            if result["success"]:
                print("OK", flush=True)
            else:
                print(
                    f"ERROR: {result['error']}",
                    file=sys.stderr, flush=True,
                )
                return 2
        else:
            print("SKIPPED", flush=True)

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
