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

"""Password hashing utilities using Argon2id algorithm.

This module provides secure password hashing following the OAuth2 Implementation Spec:
- Algorithm: Argon2id
- Memory Cost: 65536 KB (64 MB)
- Time Cost: 3 iterations
- Parallelism: 4 threads
- Salt Length: 16 bytes
- Hash Length: 32 bytes
"""

import logging
import secrets
from typing import Tuple

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError

logger = logging.getLogger(__name__)

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id.

    Args:
        password: The plaintext password to hash.

    Returns:
        The hashed password in Argon2 PHC string format.
    """
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash.

    Args:
        password: The plaintext password to verify.
        hashed: The Argon2 hash to verify against.

    Returns:
        True if password matches, False otherwise.
    """
    try:
        _hasher.verify(hashed, password)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def check_needs_rehash(hashed: str) -> bool:
    """Check if a hash needs to be rehashed due to parameter changes.

    Args:
        hashed: The existing hash to check.

    Returns:
        True if rehashing is recommended, False otherwise.
    """
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True


def generate_client_id() -> str:
    """Generate a unique client ID.

    Returns:
        A client ID with 'bld_' prefix followed by 32 hex characters.
    """
    return f"bld_{secrets.token_hex(16)}"


def generate_client_secret() -> str:
    """Generate a cryptographically secure client secret.

    Returns:
        A client secret with 'bld_s_' prefix followed by URL-safe base64 characters.
    """
    return f"bld_s_{secrets.token_urlsafe(32)}"


def generate_credentials() -> Tuple[str, str, str]:
    """Generate a new client ID, secret, and hashed secret.

    Returns:
        Tuple of (client_id, client_secret, hashed_secret).
        The client_secret is the plaintext to return to the client.
        The hashed_secret is what should be stored in the vault.
    """
    client_id = generate_client_id()
    client_secret = generate_client_secret()
    hashed_secret = hash_password(client_secret)


    return client_id, client_secret, hashed_secret
