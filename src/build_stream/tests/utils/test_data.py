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

"""Utilities for generating secure test data.

This module provides functions to generate random test data
without using hard-coded values that could be security vulnerabilities.
"""

import secrets
import string
from typing import Tuple


def generate_secure_password(length: int = 16) -> str:
    """Generate a cryptographically secure random password.

    Args:
        length: Length of the password (default: 16)

    Returns:
        Random password meeting strength requirements
    """
    # Ensure minimum length for security
    if length < 8:
        raise ValueError("Password length must be at least 8 characters")

    # Character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*"

    # Start with one of each required character type
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special),
    ]

    # Fill remaining length with random characters from all sets
    all_chars = lowercase + uppercase + digits + special
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))

    # Shuffle to avoid predictable pattern
    secrets.SystemRandom().shuffle(password)

    return ''.join(password)


def generate_password_pair(length: int = 16) -> Tuple[str, str]:
    """Generate a pair of different secure passwords.

    Args:
        length: Length of each password (default: 16)

    Returns:
        Tuple of two different passwords
    """
    password1 = generate_secure_password(length)
    password2 = generate_secure_password(length)

    # Ensure they're different
    while password2 == password1:
        password2 = generate_secure_password(length)

    return password1, password2


def generate_test_string(prefix: str = "test", length: int = 10) -> str:
    """Generate a random test string with optional prefix.

    Args:
        prefix: Optional prefix for the string
        length: Length of random part (excluding prefix)

    Returns:
        Random string with prefix
    """
    random_part = ''.join(secrets.choice(string.ascii_lowercase + string.digits)
                         for _ in range(length))
    return f"{prefix}_{random_part}" if prefix else random_part


def generate_test_email(domain: str = "example.com") -> str:
    """Generate a random test email address.

    Args:
        domain: Domain for the email

    Returns:
        Random test email
    """
    local = generate_test_string("user", 8)
    return f"{local}@{domain}"


def generate_test_client_name() -> str:
    """Generate a random test client name.

    Returns:
        Random client name following validation rules
    """
    # Generate name that starts with alphanumeric and contains only allowed chars
    first_char = secrets.choice(string.ascii_lowercase + string.digits)
    rest = ''.join(secrets.choice(string.ascii_lowercase + string.digits + '-_')
                   for _ in range(10))
    return first_char + rest
