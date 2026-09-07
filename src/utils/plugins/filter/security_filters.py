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
Ansible filter plugins for security operations.
"""

import secrets
import re


def secure_random_password(length=32):
    """
    Generate a cryptographically secure random password.
    
    Args:
        length: Length of password (default 32)
        
    Returns:
        Secure random password string
    """
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(secrets.choice(alphabet) for _ in range(int(length)))


def sanitize_log_message(message):
    """
    Sanitize log messages to prevent information disclosure.
    
    Args:
        message: Original log message
        
    Returns:
        Sanitized log message
    """
    if not message:
        return ""
    
    # Remove absolute paths
    sanitized = re.sub(r'/[a-zA-Z0-9/_\-\.]+', '<path>', str(message))
    
    # Remove IP addresses
    sanitized = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '<ip>', sanitized)
    
    # Remove hostnames (but preserve error types)
    sanitized = re.sub(r'\b[a-z0-9\-]+\.[a-z0-9\-\.]+\b', '<host>', sanitized)
    
    # Truncate if too long
    if len(sanitized) > 200:
        sanitized = sanitized[:200] + "..."
    
    return sanitized


def validate_nfs_input(value, input_type='server'):
    """
    Validate NFS-related input for security.
    
    Args:
        value: Input value to validate
        input_type: Type of input ('server' or 'path')
        
    Returns:
        Validation result dict with 'valid' and 'message' keys
    """
    if not value:
        return {'valid': False, 'message': f'NFS {input_type} cannot be empty'}
    
    if input_type == 'server':
        # Check for command injection characters
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r']
        if any(char in value for char in dangerous_chars):
            return {'valid': False, 'message': 'NFS server contains invalid characters'}
        
        # Validate hostname or IP pattern
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        ipv4_pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        
        if not (re.match(hostname_pattern, value) or re.match(ipv4_pattern, value)):
            return {'valid': False, 'message': 'NFS server format is invalid'}
            
    elif input_type == 'path':
        # Check for command injection characters
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r', '*', '?']
        if any(char in value for char in dangerous_chars):
            return {'valid': False, 'message': 'NFS path contains invalid characters'}
        
        # Must be absolute path
        if not value.startswith('/'):
            return {'valid': False, 'message': 'NFS path must be absolute'}
        
        # Check for path traversal
        if '..' in value:
            return {'valid': False, 'message': 'NFS path cannot contain ..'}
    
    return {'valid': True, 'message': 'Valid'}


class FilterModule:
    """Ansible filter plugin class."""
    
    def filters(self):
        """Return filter mappings."""
        return {
            'secure_random_password': secure_random_password,
            'sanitize_log_message': sanitize_log_message,
            'validate_nfs_input': validate_nfs_input,
        }
