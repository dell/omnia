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

"""Orchestrator credential, key, log, and vault protection contracts."""

import pytest
from library.functions import (
    check_credential_file_permissions,
    check_log_file_permissions,
    check_ssh_private_key_permissions,
    check_vault_encryption,
)

from nft.result import verify_nft

pytestmark = [pytest.mark.nft, pytest.mark.security]


@pytest.mark.order(60)
def test_credential_file_permissions(host):
    """Require restricted permissions on encrypted product credentials."""
    verify_nft(host, "credential_file_permissions", check_credential_file_permissions)


@pytest.mark.order(61)
def test_ssh_private_key_permissions(host):
    """Require root-only access to the OIM private key."""
    verify_nft(host, "ssh_private_key_permissions", check_ssh_private_key_permissions)


@pytest.mark.order(62)
def test_log_file_permissions(host):
    """Require Orchestrator logs to remain unavailable to other users."""
    verify_nft(host, "log_file_permissions", check_log_file_permissions)


@pytest.mark.order(63)
def test_vault_encryption(host):
    """Require supported vault encryption and a protected vault key."""
    verify_nft(host, "vault_encryption", check_vault_encryption)
