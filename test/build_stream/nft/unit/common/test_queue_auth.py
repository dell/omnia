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

"""Tests for authenticated playbook queue messages."""

import os

import pytest

from common.queue_auth import (
    MAX_MESSAGE_BYTES,
    QueueAuthenticationError,
    create_signed_envelope,
    load_auth_key,
    read_signed_payload,
    verify_signed_envelope,
    write_signed_payload,
)

KEY = b"k" * 32


def test_auth_key_requires_private_permissions(tmp_path):
    key_path = tmp_path / "queue.key"
    key_path.write_bytes(KEY)
    key_path.chmod(0o640)

    with pytest.raises(QueueAuthenticationError, match="group or others"):
        load_auth_key(str(key_path))


def test_signed_request_round_trip():
    payload = {"request_id": "request-1", "job_id": "job-1"}
    envelope = create_signed_envelope(
        payload, KEY, purpose="request", now=1000, ttl_seconds=60
    )

    assert verify_signed_envelope(
        envelope, KEY, purpose="request", now=1030
    ) == payload


def test_tampered_payload_is_rejected():
    envelope = create_signed_envelope(
        {"playbook_path": "repo_manager.yml"}, KEY, purpose="request"
    )
    envelope["payload"]["playbook_path"] = "orchestrator.yml"

    with pytest.raises(QueueAuthenticationError, match="authentication failed"):
        verify_signed_envelope(envelope, KEY, purpose="request")


def test_cross_channel_envelope_is_rejected():
    envelope = create_signed_envelope(
        {"request_id": "request-1"}, KEY, purpose="result"
    )

    with pytest.raises(QueueAuthenticationError, match="purpose"):
        verify_signed_envelope(envelope, KEY, purpose="request")


def test_expired_envelope_is_rejected():
    envelope = create_signed_envelope(
        {"request_id": "request-1"},
        KEY,
        purpose="request",
        now=1000,
        ttl_seconds=60,
    )

    with pytest.raises(QueueAuthenticationError, match="expired"):
        verify_signed_envelope(
            envelope, KEY, purpose="request", now=1200
        )


def test_signed_file_is_atomic_and_mode_0600(tmp_path):
    target = tmp_path / "requests" / "request.json"
    payload = {"request_id": "request-1"}

    write_signed_payload(target, payload, KEY, purpose="request")

    assert read_signed_payload(
        target, KEY, purpose="request"
    ) == payload
    assert target.stat().st_mode & 0o777 == 0o600
    assert not list(target.parent.glob("*.tmp"))


def test_duplicate_json_keys_are_rejected(tmp_path):
    target = tmp_path / "duplicate.json"
    target.write_text('{"version":1,"version":1}', encoding="utf-8")

    with pytest.raises(QueueAuthenticationError, match="Duplicate JSON key"):
        read_signed_payload(target, KEY, purpose="request")


def test_symbolic_link_message_is_rejected(tmp_path):
    real_file = tmp_path / "real.json"
    write_signed_payload(
        real_file, {"request_id": "request-1"}, KEY, purpose="request"
    )
    link = tmp_path / "link.json"
    link.symlink_to(real_file)

    with pytest.raises(QueueAuthenticationError, match="Unable to open"):
        read_signed_payload(link, KEY, purpose="request")


def test_oversized_message_is_rejected(tmp_path):
    target = tmp_path / "large.json"
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        os.write(descriptor, b"x" * (MAX_MESSAGE_BYTES + 1))
    finally:
        os.close(descriptor)

    with pytest.raises(QueueAuthenticationError, match="size limit"):
        read_signed_payload(target, KEY, purpose="request")
