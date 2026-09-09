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

"""Internal validation for SSH options accepted by public helpers."""

import re
import shlex
from typing import List, Sequence, Union


_OPTION_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_SSH_USER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}")
_SSH_HOST_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:%-]{0,252}")
_BLOCKED_OPTIONS = frozenset({
    "include",
    "knownhostscommand",
    "localcommand",
    "permitlocalcommand",
    "proxycommand",
    "remotecommand",
})
_ALLOWED_OPTIONS = frozenset({
    "addressfamily",
    "batchmode",
    "ciphers",
    "compression",
    "connectionattempts",
    "connecttimeout",
    "globalknownhostsfile",
    "hashknownhosts",
    "hostkeyalgorithms",
    "hostkeyalias",
    "identitiesonly",
    "identityfile",
    "kexalgorithms",
    "loglevel",
    "macs",
    "numberofpasswordprompts",
    "passwordauthentication",
    "preferredauthentications",
    "pubkeyauthentication",
    "rekeylimit",
    "serveralivecountmax",
    "serveraliveinterval",
    "stricthostkeychecking",
    "userknownhostsfile",
})


def validate_ssh_destination(host: str, user: str) -> tuple[str, str]:
    """Validate and normalize a host/user pair used as an SSH operand."""
    if not isinstance(host, str) or not _SSH_HOST_RE.fullmatch(host.strip()):
        raise ValueError("SSH host contains unsupported characters")
    if not isinstance(user, str) or not _SSH_USER_RE.fullmatch(user.strip()):
        raise ValueError("SSH user contains unsupported characters")
    return host.strip(), user.strip()


def validate_ssh_port(port: object) -> int:
    """Return an SSH TCP port in the valid 1-65535 range."""
    if isinstance(port, bool):
        raise ValueError("SSH port must be an integer from 1 to 65535")
    try:
        normalized = int(port)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "SSH port must be an integer from 1 to 65535"
        ) from exc
    if str(normalized) != str(port).strip() or not 1 <= normalized <= 65535:
        raise ValueError("SSH port must be an integer from 1 to 65535")
    return normalized


def parse_ssh_options(value: Union[str, Sequence[str]]) -> List[str]:
    """Return validated ``ssh -o Name=value`` arguments.

    Command-bearing OpenSSH directives are intentionally rejected. Public
    helpers need connection tuning, not a second command-execution channel.
    """
    if isinstance(value, str):
        try:
            tokens = shlex.split(value)
        except ValueError as exc:
            raise ValueError(f"Invalid SSH options: {exc}") from exc
    elif isinstance(value, (list, tuple)) and all(
        isinstance(token, str) for token in value
    ):
        tokens = list(value)
    else:
        raise ValueError("SSH options must be text or a sequence of strings")

    parsed: List[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "-o":
            if index + 1 >= len(tokens):
                raise ValueError("SSH -o requires a Name=value argument")
            option = tokens[index + 1]
            index += 2
        elif token.startswith("-o") and len(token) > 2:
            option = token[2:]
            index += 1
        else:
            raise ValueError(
                "Only OpenSSH -o Name=value options are supported"
            )

        if "=" not in option:
            raise ValueError("SSH options must use Name=value syntax")
        name, option_value = option.split("=", 1)
        if not _OPTION_NAME_RE.fullmatch(name) or not option_value:
            raise ValueError("SSH options must use a valid Name=value syntax")
        normalized_name = name.lower()
        normalized_value = option_value.lower()
        if normalized_name in _BLOCKED_OPTIONS:
            raise ValueError(f"Unsupported command-bearing SSH option: {name}")
        if normalized_name not in _ALLOWED_OPTIONS:
            raise ValueError(f"Unsupported SSH option: {name}")
        if normalized_name == "stricthostkeychecking" and normalized_value in {
            "false", "no", "off",
        }:
            raise ValueError("StrictHostKeyChecking may not be disabled")
        if normalized_name == "userknownhostsfile":
            known_hosts_paths = shlex.split(option_value)
            if any(
                path.lower() in {"/dev/null", "none"}
                for path in known_hosts_paths
            ):
                raise ValueError(
                    "The SSH known-hosts database may not be disabled"
                )
        parsed.extend(["-o", option])

    return parsed
