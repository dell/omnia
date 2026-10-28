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
File I/O utilities for build_stream input validation.

Provides YAML/JSON loading and Ansible Vault detection.
"""
import json
import logging
import os
import subprocess
from typing import Any, Optional, Tuple

import yaml

from ansible.module_utils.input_validation.core.config import VAULT_HEADER  # pylint: disable=E0401


def is_vault_encrypted(path) -> bool:
    """Check if a file is Ansible Vault encrypted."""
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    return first_line.startswith(VAULT_HEADER)


def load_vault_yaml(path) -> Tuple[Any, Optional[str], bool]:
    """Decrypt a vault file in memory with its sibling ``.<stem>_key`` file.

    Returns:
        (data, error, key_available). key_available is False when no vault key
        exists, in which case the file cannot be validated.
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    key_path = os.path.join(os.path.dirname(path), f".{stem}_key")
    if not os.path.isfile(key_path):
        return None, None, False
    try:
        result = subprocess.run(
            ["ansible-vault", "view", path, "--vault-password-file", key_path],
            capture_output=True, text=True, check=False, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"Unable to decrypt vault file {path}: {exc}", True
    if result.returncode != 0:
        return None, f"Unable to decrypt vault file {path}: {result.stderr.strip()}", True
    try:
        return yaml.safe_load(result.stdout), None, True
    except yaml.YAMLError:
        return None, f"Failed to parse decrypted YAML: {path}", True


REDACTED = "********"


def collect_secret_strings(data) -> list:
    """Return every scalar value (not key) in decrypted data, longest first."""
    found, stack = set(), [data]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, str) and item:
            found.add(item)
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            found.add(str(item))
    return sorted(found, key=len, reverse=True)


def redact(text, secrets) -> str:
    """Mask any decrypted secret value that appears in a message.

    Quoted (repr) forms are always masked; bare substrings only for values of
    3+ characters so short values do not mangle unrelated message text.
    """
    text = str(text)
    for secret in secrets:
        text = text.replace(repr(secret), REDACTED)
        if len(secret) >= 3:
            text = text.replace(secret, REDACTED)
    return text


class RedactingLogger(logging.LoggerAdapter):
    """Logger adapter that masks decrypted secret values in log messages."""

    def __init__(self, logger, secrets):
        super().__init__(logger, {})
        self.secrets = secrets

    def process(self, msg, kwargs):
        return redact(msg, self.secrets), kwargs


def load_yaml(path) -> Any:
    """Load a YAML file, returning None on failure."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path) -> Any:
    """Load a JSON file, returning None on failure."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
