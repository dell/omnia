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
Security utility functions for input validation and sanitization.
"""

import re
import secrets
from pathlib import Path
from typing import Tuple, Optional


def validate_nfs_server(nfs_server: str) -> Tuple[bool, str]:
    """
    Validate NFS server address (hostname or IP).

    Args:
        nfs_server: NFS server hostname or IP address

    Returns:
        Tuple of (is_valid, error_message)
    """
    result = True, ""

    if not nfs_server or not isinstance(nfs_server, str):
        return False, "NFS server cannot be empty"

    # Remove whitespace
    nfs_server = nfs_server.strip()

    # Check length
    if len(nfs_server) > 253:
        return False, "NFS server name too long (max 253 characters)"

    # Check for command injection characters
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r']
    if any(char in nfs_server for char in dangerous_chars):
        return False, "NFS server contains invalid characters"

    # Validate hostname pattern (RFC 1123)
    hostname_pattern = (
        r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'
        r'(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    )

    # Validate IPv4 pattern
    ipv4_pattern = (
        r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )

    # Validate IPv6 pattern (simplified)
    ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){7}[0-9a-fA-F]{0,4}$'

    if not (re.match(hostname_pattern, nfs_server) or
            re.match(ipv4_pattern, nfs_server) or
            re.match(ipv6_pattern, nfs_server)):
        return False, "NFS server format is invalid (not a valid hostname or IP)"

    return result


def validate_nfs_path(nfs_path: str) -> Tuple[bool, str]:
    """
    Validate NFS export path.

    Args:
        nfs_path: NFS export path

    Returns:
        Tuple of (is_valid, error_message)
    """
    result = True, ""

    if not nfs_path or not isinstance(nfs_path, str):
        return False, "NFS path cannot be empty"

    # Check for command injection characters
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r', '*', '?']
    if any(char in nfs_path for char in dangerous_chars):
        return False, "NFS path contains invalid characters"

    # Must be absolute path
    if not nfs_path.startswith('/'):
        return False, "NFS path must be absolute (start with /)"

    # Check for path traversal
    if '..' in nfs_path:
        return False, "NFS path cannot contain '..' (path traversal)"

    # Check length
    if len(nfs_path) > 4096:
        return False, "NFS path too long (max 4096 characters)"

    # Validate path components
    path_pattern = r'^/[a-zA-Z0-9/_\-\.]+$'
    if not re.match(path_pattern, nfs_path):
        return False, "NFS path contains invalid characters"

    return result


def validate_file_path(
    file_path: str,
    allowed_base_dirs: Optional[list] = None
) -> Tuple[bool, str]:
    """
    Validate file path for security issues.

    Args:
        file_path: File path to validate
        allowed_base_dirs: List of allowed base directories (optional)

    Returns:
        Tuple of (is_valid, error_message)
    """
    result = True, ""

    if not file_path or not isinstance(file_path, str):
        return False, "File path cannot be empty"

    # Check for command injection characters
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r']
    if any(char in file_path for char in dangerous_chars):
        return False, "File path contains invalid characters"

    # Check for path traversal
    if '..' in file_path:
        return False, "File path cannot contain '..' (path traversal)"

    # Resolve to absolute path
    try:
        resolved_path = Path(file_path).resolve()
    except (ValueError, RuntimeError) as e:
        return False, f"Invalid file path: {str(e)}"

    # Check against allowed base directories
    if allowed_base_dirs:
        allowed = False
        for base_dir in allowed_base_dirs:
            try:
                resolved_base = Path(base_dir).resolve()
                if resolved_path.is_relative_to(resolved_base):
                    allowed = True
                    break
            except (ValueError, RuntimeError, AttributeError):
                # AttributeError for Python < 3.9 (is_relative_to)
                # Fallback to string comparison
                if str(resolved_path).startswith(str(Path(base_dir).resolve())):
                    allowed = True
                    break

        if not allowed:
            return False, f"File path not in allowed directories: {', '.join(allowed_base_dirs)}"

    return result


def sanitize_error_message(error_msg: str) -> str:
    """
    Sanitize error messages to prevent information disclosure.
    
    Args:
        error_msg: Original error message
        
    Returns:
        Sanitized error message
    """
    if not error_msg:
        return "An error occurred"

    # Remove absolute paths
    sanitized = re.sub(r'/[a-zA-Z0-9/_\-\.]+', '<path>', error_msg)

    # Remove IP addresses
    sanitized = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '<ip>', sanitized)

    # Remove hostnames
    sanitized = re.sub(r'\b[a-z0-9\-]+\.[a-z0-9\-\.]+\b', '<host>', sanitized)

    # Truncate if too long
    if len(sanitized) > 200:
        sanitized = sanitized[:200] + "..."

    return sanitized


def generate_vault_key(length: int = 32) -> str:
    """
    Generate a cryptographically secure vault key.
    
    Args:
        length: Length of the key (default 32)
        
    Returns:
        Secure random key string
    """
    # Use secrets module for cryptographically secure random generation
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def validate_iso_filename(filename: str) -> Tuple[bool, str]:
    """
    Validate ISO filename for security.
    
    Args:
        filename: ISO filename to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename or not isinstance(filename, str):
        return False, "Filename cannot be empty"

    # Check for command injection characters
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r', '/', '\\']
    if any(char in filename for char in dangerous_chars):
        return False, "Filename contains invalid characters"

    # Check for path traversal
    if '..' in filename:
        return False, "Filename cannot contain '..'"

    # Must end with .iso
    if not filename.lower().endswith('.iso'):
        return False, "Filename must end with .iso"

    # Validate filename pattern
    filename_pattern = r'^[a-zA-Z0-9_\-\.]+\.iso$'
    if not re.match(filename_pattern, filename, re.IGNORECASE):
        return False, "Filename format is invalid"

    return True, ""
