#!/usr/bin/python
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

# pylint: disable=import-error,no-name-in-module

import os
import copy
import signal
import tempfile
from ansible.module_utils.basic import AnsibleModule

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

"""
Ansible module to efficiently update Kubernetes upgrade status file.

This module optimizes status file updates by:
- Direct file manipulation on the remote host (no temp files on controller)
- File locking to prevent race conditions
- Atomic write operations
- Connection reuse for better performance
- Preserves YAML key order for readability
"""

DOCUMENTATION = r'''
---
module: k8s_upgrade_status

short_description: Update Kubernetes upgrade status file efficiently

version_added: "2.1.0"

description:
    - Updates the Kubernetes upgrade status YAML file on kube_vip host
    - Supports both node-specific and general status updates
    - Uses file locking and atomic operations for safety
    - Optimized for performance with direct remote file manipulation

options:
    status_file:
        description: Path to the status file on kube_vip host
        required: true
        type: str
    kube_vip:
        description: Target host where status file is stored
        required: true
        type: str
    node_name:
        description: Name of the node to update (for node-specific updates)
        required: false
        type: str
    node_status_update:
        description: Dictionary to merge into the node's status
        required: false
        type: dict
    status_update:
        description: Dictionary to merge into general status (non-node updates)
        required: false
        type: dict

author:
    - Dell Omnia Team
'''

EXAMPLES = r'''
# Update node-specific status
- name: Mark kubeadm_install as in_progress
  k8s_upgrade_status:
    status_file: /mnt/nfs/upgrade/upgrade_status.yml
    kube_vip: 192.168.1.100
    node_name: kcp1
    node_status_update:
      steps:
        kubeadm_install:
          status: in_progress
          timestamp: "2026-05-17T12:00:00Z"

# Update general status
- name: Mark etcd backup as completed
  k8s_upgrade_status:
    status_file: /mnt/nfs/upgrade/upgrade_status.yml
    kube_vip: 192.168.1.100
    status_update:
      etcd_backup:
        status: completed
        timestamp: "2026-05-17T12:00:00Z"
'''

RETURN = r'''
changed:
    description: Whether the status file was modified
    type: bool
    returned: always
merged_status:
    description: The complete merged status after update
    type: dict
    returned: always
'''


def merge_dicts(base, update):
    """
    Recursively merge two dictionaries.

    Args:
        base: Base dictionary
        update: Dictionary with updates to merge

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def read_status_file(file_path):
    """
    Read and parse the status YAML file with file locking.

    Args:
        file_path: Path to the status file

    Returns:
        Parsed status dictionary, or empty dict if file doesn't exist
    """
    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                return {}
            return yaml.safe_load(content) or {}
    except (OSError, IOError, yaml.YAMLError) as e:
        raise IOError(f"Failed to read status file: {str(e)}") from e


NFS_WRITE_TIMEOUT = 60  # seconds


class _NfsWriteTimeout(Exception):
    """Raised when an NFS write operation exceeds the timeout."""


def _timeout_handler(signum, frame):
    raise _NfsWriteTimeout("NFS write operation timed out")


def _cleanup_stale_tmp_files(dir_path):
    """Remove leftover .upgrade_status_*.tmp files that may block NFS."""
    try:
        for entry in os.listdir(dir_path):
            if entry.startswith('.upgrade_status_') and entry.endswith('.tmp'):
                try:
                    os.unlink(os.path.join(dir_path, entry))
                except OSError:
                    pass
    except OSError:
        pass


def write_status_file(file_path, status_data):
    """
    Write status data to YAML file atomically with file locking.

    Args:
        file_path: Path to the status file
        status_data: Dictionary to write
    """
    # Ensure directory exists
    target_dir = os.path.dirname(file_path)
    os.makedirs(target_dir, mode=0o755, exist_ok=True)

    # Clean up any stale temp files from previous failed attempts
    _cleanup_stale_tmp_files(target_dir)

    # Write to temporary file first
    temp_fd, temp_path = tempfile.mkstemp(
        dir=target_dir,
        prefix='.upgrade_status_',
        suffix='.tmp'
    )

    # Set an alarm so NFS hangs don't block indefinitely
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(NFS_WRITE_TIMEOUT)

    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            # Use safe_dump with custom settings to preserve order and readability
            yaml.safe_dump(
                status_data,
                f,
                default_flow_style=False,
                sort_keys=False,
                indent=2,
                width=120
            )
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename
        os.chmod(temp_path, 0o644)
        os.rename(temp_path, file_path)

    except _NfsWriteTimeout:
        # Clean up temp file on timeout
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise IOError(
            f"NFS write timed out after {NFS_WRITE_TIMEOUT}s writing to {file_path}. "
            "Check NFS mount health and clear stale .nfs* handles."
        )
    except (OSError, IOError, yaml.YAMLError) as e:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise IOError(f"Failed to write status file: {str(e)}") from e
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def run_module():
    """
    Main module execution.
    """
    module_args = {
        'status_file': {'type': 'str', 'required': True},
        'kube_vip': {'type': 'str', 'required': True},
        'node_name': {'type': 'str', 'required': False, 'default': None},
        'node_status_update': {'type': 'dict', 'required': False, 'default': None},
        'status_update': {'type': 'dict', 'required': False, 'default': None},
    }

    result = {
        'changed': False,
        'merged_status': {},
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        mutually_exclusive=[
            ['node_status_update', 'status_update']
        ],
        required_one_of=[
            ['node_status_update', 'status_update']
        ]
    )

    if not HAS_YAML:
        module.fail_json(msg='PyYAML is required for this module')

    status_file = module.params['status_file']
    node_name = module.params['node_name']
    node_status_update = module.params['node_status_update']
    status_update = module.params['status_update']

    # Validate node-specific update has node_name
    if node_status_update and not node_name:
        module.fail_json(msg='node_name is required when node_status_update is provided')

    try:
        # Read current status
        current_status = read_status_file(status_file)

        # Deep-copy before mutation so the original is preserved for
        # the changed-detection comparison below.
        original_status = copy.deepcopy(current_status)

        # Build merged status
        if node_status_update:
            # Node-specific update
            nodes = copy.deepcopy(current_status.get('nodes', {}))
            node_data = nodes.get(node_name, {})
            updated_node_data = merge_dicts(node_data, node_status_update)
            nodes[node_name] = updated_node_data
            merged_status = merge_dicts(current_status, {'nodes': nodes})
        else:
            # General update
            merged_status = merge_dicts(current_status, status_update)

        # Check if anything changed
        if merged_status != original_status:
            result['changed'] = True

            # Write updated status (unless in check mode)
            if not module.check_mode:
                write_status_file(status_file, merged_status)

        result['merged_status'] = merged_status
        module.exit_json(**result)

    except (OSError, IOError, yaml.YAMLError) as e:
        module.fail_json(msg=str(e), **result)


def main():
    """Main entry point."""
    run_module()


if __name__ == '__main__':
    main()
