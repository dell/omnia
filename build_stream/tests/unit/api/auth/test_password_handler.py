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

"""Unit tests for password_handler module."""

import pytest

from api.auth.password_handler import (
    generate_client_id,
    generate_client_secret,
    generate_credentials,
    hash_password,
    verify_password,
)
from tests.utils.test_data import generate_secure_password, generate_password_pair


@pytest.fixture
def test_password():
    """Generate a random test password for each test."""
    return generate_secure_password(16)


@pytest.fixture
def test_password_pair():
    """Generate a pair of different test passwords."""
    return generate_password_pair(16)


@pytest.mark.unit
class TestPasswordHashing:
    """Test suite for password hashing functions."""

    def test_hash_password_returns_argon2_hash(self, test_password):  # noqa: W0621
        """Test that hash_password returns Argon2id hash."""
        hashed = hash_password(test_password)

        assert hashed.startswith("$argon2id$")
        assert test_password not in hashed

    def test_hash_password_different_for_same_input(self, test_password):  # noqa: W0621
        """Test that hashing same password twice produces different hashes."""
        hash1 = hash_password(test_password)
        hash2 = hash_password(test_password)

        assert hash1 != hash2

    def test_verify_password_correct_password(self, test_password):  # noqa: W0621
        """Test verify_password returns True for correct password."""
        hashed = hash_password(test_password)

        assert verify_password(test_password, hashed) is True

    def test_verify_password_incorrect_password(self, test_password_pair):  # noqa: W0621
        """Test verify_password returns False for incorrect password."""
        correct_password, wrong_password = test_password_pair
        hashed = hash_password(correct_password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_invalid_hash(self, test_password):  # noqa: W0621
        """Test verify_password returns False for invalid hash."""
        assert verify_password(test_password, "invalid_hash") is False

    def test_generated_password_strength(self, test_password):  # noqa: W0621
        """Test that generated passwords meet strength requirements."""
        # Password should be at least 16 characters
        assert len(test_password) >= 16

        # Should contain at least one lowercase letter
        assert any(c.islower() for c in test_password)

        # Should contain at least one uppercase letter
        assert any(c.isupper() for c in test_password)

        # Should contain at least one digit
        assert any(c.isdigit() for c in test_password)

        # Should contain at least one special character
        special_chars = "!@#$%^&*"
        assert any(c in special_chars for c in test_password)


@pytest.mark.unit
class TestCredentialGeneration:
    """Test suite for credential generation functions."""

    def test_generate_client_id_format(self):
        """Test client_id has correct format."""
        client_id = generate_client_id()

        assert client_id.startswith("bld_")
        assert len(client_id) == 36

    def test_generate_client_id_unique(self):
        """Test client_id is unique each time."""
        ids = [generate_client_id() for _ in range(100)]

        assert len(set(ids)) == 100

    def test_generate_client_secret_format(self):
        """Test client_secret has correct format."""
        client_secret = generate_client_secret()

        assert client_secret.startswith("bld_s_")
        assert len(client_secret) > 40

    def test_generate_client_secret_unique(self):
        """Test client_secret is unique each time."""
        secrets = [generate_client_secret() for _ in range(100)]

        assert len(set(secrets)) == 100

    def test_generate_credentials_returns_tuple(self):
        """Test generate_credentials returns correct tuple."""
        client_id, client_secret, hashed_secret = generate_credentials()

        assert client_id.startswith("bld_")
        assert client_secret.startswith("bld_s_")
        assert hashed_secret.startswith("$argon2id$")

    def test_generate_credentials_secret_verifiable(self):
        """Test that generated secret can be verified against hash."""
        _, client_secret, hashed_secret = generate_credentials()

        assert verify_password(client_secret, hashed_secret) is True
