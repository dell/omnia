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

"""Authentication and safe I/O for the privileged playbook queue."""

import hashlib
import hmac
import json
import os
import stat
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

AUTH_KEY_ENV = "PLAYBOOK_QUEUE_AUTH_KEY_FILE"
DEFAULT_AUTH_KEY_FILE = "/run/secrets/omnia-playbook-queue.key"
ENVELOPE_VERSION = 1
ENVELOPE_FIELDS = {
    "version",
    "purpose",
    "issued_at",
    "expires_at",
    "payload",
    "mac",
}
VALID_PURPOSES = {"request", "result", "pending"}
MIN_KEY_BYTES = 32
DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_TTL_SECONDS = DEFAULT_TTL_SECONDS
MAX_CLOCK_SKEW_SECONDS = 60
MAX_MESSAGE_BYTES = 1024 * 1024


class QueueAuthenticationError(ValueError):
    """Raised when a queue message cannot be authenticated."""


def _reject_duplicate_keys(pairs):
    """Build a JSON object while rejecting ambiguous duplicate keys."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise QueueAuthenticationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_json(value: Any) -> bytes:
    """Return the unique JSON representation used by the MAC."""
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise QueueAuthenticationError(
            "Queue payload is not canonical JSON"
        ) from exc
    return encoded.encode("utf-8")


def _validate_purpose(purpose: str) -> str:
    if purpose not in VALID_PURPOSES:
        raise QueueAuthenticationError("Invalid queue message purpose")
    return purpose


def load_auth_key(key_path: Optional[str] = None) -> bytes:
    """Load a root-managed queue key without following symbolic links."""
    resolved_path = Path(
        key_path or os.environ.get(AUTH_KEY_ENV, DEFAULT_AUTH_KEY_FILE)
    )
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        descriptor = os.open(resolved_path, flags)
    except OSError as exc:
        raise QueueAuthenticationError(
            f"Unable to open queue authentication key: {resolved_path}"
        ) from exc

    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise QueueAuthenticationError(
                "Queue authentication key is not a file"
            )
        if metadata.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise QueueAuthenticationError(
                "Queue authentication key must not be accessible by group or others"
            )
        key = os.read(descriptor, MIN_KEY_BYTES + 1)
        if len(key) < MIN_KEY_BYTES:
            raise QueueAuthenticationError(
                f"Queue authentication key must be at least {MIN_KEY_BYTES} bytes"
            )
        return key
    finally:
        os.close(descriptor)


def _mac_input(
    version: int,
    purpose: str,
    issued_at: int,
    expires_at: int,
    payload: Any,
) -> bytes:
    signed_data = {
        "expires_at": expires_at,
        "issued_at": issued_at,
        "payload": payload,
        "purpose": purpose,
        "version": version,
    }
    domain = f"omnia-playbook-queue:{purpose}:v{version}\n".encode("ascii")
    return domain + _canonical_json(signed_data)


def create_signed_envelope(
    payload: Dict[str, Any],
    key: bytes,
    *,
    purpose: str,
    now: Optional[int] = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> Dict[str, Any]:
    """Create a versioned, time-bounded authenticated queue envelope."""
    purpose = _validate_purpose(purpose)
    if not isinstance(payload, dict):
        raise QueueAuthenticationError("Queue payload must be an object")
    if len(key) < MIN_KEY_BYTES:
        raise QueueAuthenticationError("Queue authentication key is too short")
    if isinstance(ttl_seconds, bool) or not 1 <= ttl_seconds <= MAX_TTL_SECONDS:
        raise QueueAuthenticationError("Invalid queue message lifetime")

    issued_at = int(time.time()) if now is None else int(now)
    expires_at = issued_at + ttl_seconds
    mac = hmac.new(
        key,
        _mac_input(
            ENVELOPE_VERSION, purpose, issued_at, expires_at, payload
        ),
        hashlib.sha256,
    ).hexdigest()
    return {
        "version": ENVELOPE_VERSION,
        "purpose": purpose,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "payload": payload,
        "mac": mac,
    }


def verify_signed_envelope(
    envelope: Dict[str, Any],
    key: bytes,
    *,
    purpose: str,
    now: Optional[int] = None,
) -> Dict[str, Any]:
    """Verify an authenticated envelope and return its payload."""
    purpose = _validate_purpose(purpose)
    if not isinstance(envelope, dict) or set(envelope) != ENVELOPE_FIELDS:
        raise QueueAuthenticationError("Invalid queue envelope fields")
    if len(key) < MIN_KEY_BYTES:
        raise QueueAuthenticationError("Queue authentication key is too short")

    version = envelope["version"]
    envelope_purpose = envelope["purpose"]
    issued_at = envelope["issued_at"]
    expires_at = envelope["expires_at"]
    payload = envelope["payload"]
    supplied_mac = envelope["mac"]
    if version != ENVELOPE_VERSION:
        raise QueueAuthenticationError("Unsupported queue envelope version")
    if envelope_purpose != purpose:
        raise QueueAuthenticationError("Unexpected queue message purpose")
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in (issued_at, expires_at)
    ):
        raise QueueAuthenticationError("Invalid queue envelope timestamps")
    if not isinstance(payload, dict):
        raise QueueAuthenticationError("Queue payload must be an object")
    if not isinstance(supplied_mac, str) or len(supplied_mac) != 64:
        raise QueueAuthenticationError("Invalid queue message MAC")
    if expires_at <= issued_at or expires_at - issued_at > MAX_TTL_SECONDS:
        raise QueueAuthenticationError("Invalid queue message lifetime")

    current_time = int(time.time()) if now is None else int(now)
    if issued_at > current_time + MAX_CLOCK_SKEW_SECONDS:
        raise QueueAuthenticationError("Queue message was issued in the future")
    if expires_at < current_time - MAX_CLOCK_SKEW_SECONDS:
        raise QueueAuthenticationError("Queue message has expired")

    expected_mac = hmac.new(
        key,
        _mac_input(
            version, envelope_purpose, issued_at, expires_at, payload
        ),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_mac, supplied_mac):
        raise QueueAuthenticationError(
            "Queue message authentication failed"
        )
    return payload


def read_signed_payload(
    file_path: Path,
    key: bytes,
    *,
    purpose: str,
    now: Optional[int] = None,
) -> Dict[str, Any]:
    """Read one bounded regular file and authenticate its complete JSON object."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(file_path, flags)
    except OSError as exc:
        raise QueueAuthenticationError("Unable to open queue message") from exc

    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise QueueAuthenticationError("Queue message is not a regular file")
        if metadata.st_size > MAX_MESSAGE_BYTES:
            raise QueueAuthenticationError(
                "Queue message exceeds size limit"
            )
        raw = os.read(descriptor, MAX_MESSAGE_BYTES + 1)
    finally:
        os.close(descriptor)

    if len(raw) > MAX_MESSAGE_BYTES:
        raise QueueAuthenticationError("Queue message exceeds size limit")
    try:
        envelope = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QueueAuthenticationError("Invalid queue message JSON") from exc
    return verify_signed_envelope(
        envelope, key, purpose=purpose, now=now
    )


def write_signed_payload(
    file_path: Path,
    payload: Dict[str, Any],
    key: bytes,
    *,
    purpose: str,
) -> None:
    """Atomically write a mode-0600 authenticated queue message."""
    envelope = create_signed_envelope(payload, key, purpose=purpose)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{file_path.name}.",
            suffix=".tmp",
            dir=str(file_path.parent),
        )
        temporary_path = Path(temporary_name)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as message_file:
            json.dump(
                envelope,
                message_file,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
            message_file.flush()
            os.fsync(message_file.fileno())
        os.replace(temporary_path, file_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
