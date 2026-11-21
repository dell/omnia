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

"""Custom CA certificate checks for the external GitLab integration (ER-BSM-003)."""

import os
import re
import stat
from typing import List, Optional

PEM_CERT_RE = re.compile(
    r"-----BEGIN CERTIFICATE-----\s+([A-Za-z0-9+/=\s]+?)\s*-----END CERTIFICATE-----"
)
MAX_CA_BUNDLE_BYTES = 1024 * 1024


def validate_pem_bundle(path: str) -> Optional[str]:
    """Return an error message when *path* is not a readable PEM CA bundle, else None."""
    if not os.path.isfile(path):
        return f"CA certificate file not found at {path}"
    try:
        if os.path.getsize(path) > MAX_CA_BUNDLE_BYTES:
            return f"CA certificate file {path} is larger than {MAX_CA_BUNDLE_BYTES} bytes"
        with open(path, "r", encoding="ascii") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        return f"CA certificate file {path} is not readable PEM text: {exc.__class__.__name__}"
    if "PRIVATE KEY" in text:
        return f"CA certificate file {path} contains a private key; provide certificates only"
    blocks = PEM_CERT_RE.findall(text)
    if not blocks:
        return (
            f"CA certificate file {path} is not a valid PEM bundle: "
            "no BEGIN/END CERTIFICATE block found"
        )
    for block in blocks:
        body = re.sub(r"\s+", "", block)
        if len(body) % 4 != 0 or not body:
            return f"CA certificate file {path} is not a valid PEM bundle: malformed body"
    return None


def check_permissions(path: str) -> List[str]:
    """Return problems with ownership/mode: must be root-owned, mode 0644 or stricter."""
    problems = []
    info = os.stat(path)
    if info.st_uid != 0:
        problems.append(
            f"CA certificate file {path} must be owned by root (uid {info.st_uid} found)"
        )
    if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
        problems.append(
            f"CA certificate file {path} must have mode 0644 or stricter "
            f"({stat.S_IMODE(info.st_mode):04o} found)"
        )
    return problems
