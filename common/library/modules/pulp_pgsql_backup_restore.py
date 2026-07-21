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
#!/usr/bin/python

"""
Backup and restore Pulp PostgreSQL data for upgrade/rollback.

Handles the PostgreSQL version incompatibility between Pulp versions:
  - Pulp 3.80 uses PostgreSQL 12/13
  - Pulp 3.113 uses PostgreSQL 16

Backup (action=backup):
  - Validates source PostgreSQL data exists
  - Checks PG_VERSION to confirm pre-upgrade state (PG 12 or 13)
  - Skips if a valid backup already exists
  - Copies data with ownership and SELinux context preserved
  - Verifies backup integrity

Restore (action=restore):
  The backup may contain:
  - data/ with PG 12/13: restore directly
  - data/ with PG 16 + data_old.* with PG 12/13: restore data_old as data
"""

import os
import glob
import shutil
import subprocess

from ansible.module_utils.basic import AnsibleModule


COMPATIBLE_PG_VERSIONS = ("12", "13")


def read_pg_version(data_dir):
    """Read PG_VERSION file from a PostgreSQL data directory."""
    version_file = os.path.join(data_dir, "PG_VERSION")
    if not os.path.isfile(version_file):
        return None
    try:
        with open(version_file, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except (OSError, IOError):
        return None


def find_data_old_dir(base_path):
    """Find a data_old or data_old.* directory inside base_path.

    PostgreSQL upgrade creates either:
    - data_old (no suffix) - simple upgrade
    - data_old.TIMESTAMP - timestamped backup
    """
    # First check for exact 'data_old' directory (most common)
    data_old_exact = os.path.join(base_path, "data_old")
    if os.path.isdir(data_old_exact):
        return data_old_exact

    # Then check for data_old.* pattern (timestamped)
    pattern = os.path.join(base_path, "data_old.*")
    matches = glob.glob(pattern)
    for match in matches:
        if os.path.isdir(match):
            return match
    return None


def get_dir_owner(path):
    """Get UID and GID of a directory."""
    try:
        stat = os.stat(path)
        return stat.st_uid, stat.st_gid
    except OSError:
        return None, None


def fix_ownership(path, uid, gid):
    """Recursively set ownership on a directory tree.

    PostgreSQL inside the Pulp container runs as UID 26 (postgres).
    shutil.copytree does not preserve ownership, so we must fix it
    after the copy.
    """
    try:
        for root, dirs, files in os.walk(path):
            os.chown(root, uid, gid)
            for name in files:
                os.chown(os.path.join(root, name), uid, gid)
    except OSError as exc:
        raise OSError(f"Failed to chown {path} to {uid}:{gid}: {exc}") from exc


def fix_selinux_context(path):
    """Apply container SELinux context. Non-fatal on failure."""
    try:
        subprocess.run(
            ["chcon", "-R", "system_u:object_r:container_file_t:s0", path],
            check=False, capture_output=True, timeout=120
        )
    except (subprocess.SubprocessError, OSError):
        pass


# =========================================================================
# Backup logic
# =========================================================================

def run_backup(module, params, result):
    """Backup Pulp PostgreSQL data before upgrade.

    Only backs up the PG 12/13 compatible data directory, not the entire
    pgsql folder. This avoids backing up unnecessary files like empty
    version folders, upgrade scripts, etc.

    Args:
        module: AnsibleModule instance.
        params: Dict with 'src_path', 'dest_path', 'backup_dir',
                and 'compatible_versions'.
        result: Mutable result dict.
    """
    src_path = params["src_path"]
    dest_path = params["dest_path"]
    backup_dir = params["backup_dir"]
    compat = tuple(params["compatible_versions"])

    # --- Validate source exists ---
    if not os.path.isdir(src_path):
        result["messages"].append(
            f"SKIP: Source PostgreSQL data not found at {src_path}"
        )
        result["skipped"] = True
        module.exit_json(**result)

    # --- Find compatible PG data to backup ---
    # First check data/, then data_old (if upgrade already happened)
    src_data_dir = os.path.join(src_path, "data")
    pg_ver = read_pg_version(src_data_dir)
    result["source_pg_version"] = pg_ver or "unknown"

    if pg_ver in compat:
        # data/ has compatible PG version, backup it directly
        backup_source = src_data_dir
        result["messages"].append(
            f"Source data/ contains PG {pg_ver}, will backup"
        )
    else:
        # data/ is upgraded, check for data_old with compatible version
        data_old_dir = find_data_old_dir(src_path)
        if data_old_dir:
            old_ver = read_pg_version(data_old_dir)
            if old_ver in compat:
                backup_source = data_old_dir
                result["messages"].append(
                    f"Source data/ is PG {pg_ver or 'unknown'}, "
                    f"using data_old (PG {old_ver}) for backup"
                )
            else:
                module.fail_json(
                    msg=(
                        f"Source data/ is PG {pg_ver or 'unknown'} and "
                        f"data_old is PG {old_ver or 'unknown'}. "
                        f"Cannot find PG {'/'.join(compat)} data to backup."
                    ),
                    **result
                )
        else:
            module.fail_json(
                msg=(
                    f"Source data/ is PG {pg_ver or 'unknown'} (already upgraded) "
                    f"and no data_old directory found. "
                    f"Cannot backup without PG {'/'.join(compat)} data."
                ),
                **result
            )

    # --- Skip if backup already exists with valid PG 12/13 data ---
    backup_data_dir = os.path.join(dest_path, "data")
    if os.path.isdir(backup_data_dir):
        backup_ver = read_pg_version(backup_data_dir)
        if backup_ver in compat:
            result["messages"].append(
                f"SKIP: Valid PG {backup_ver} backup already exists at {dest_path}"
            )
            result["backup_pg_version"] = backup_ver
            result["skipped"] = True
            module.exit_json(**result)

        result["messages"].append(
            f"WARNING: Existing backup has PG {backup_ver or 'unknown'}, recreating"
        )
        if not module.check_mode:
            try:
                shutil.rmtree(dest_path)
            except (OSError, IOError) as exc:
                module.fail_json(
                    msg=f"Failed to remove stale backup at {dest_path}: {exc}",
                    **result
                )

    # --- Check mode ---
    if module.check_mode:
        result["messages"].append("Check mode: no changes made")
        module.exit_json(**result)

    # --- PostgreSQL requires UID 26 (postgres user) ---
    postgres_uid, postgres_gid = 26, 26

    # --- Create backup (only the data directory) ---
    try:
        os.makedirs(dest_path, exist_ok=True)
        # Backup only the data directory, not the entire pgsql folder
        shutil.copytree(backup_source, backup_data_dir, symlinks=True)
    except (OSError, IOError, shutil.Error) as exc:
        module.fail_json(
            msg=f"Backup failed: {exc}",
            **result
        )

    # --- Fix ownership (postgres UID:GID = 26:26) ---
    try:
        fix_ownership(dest_path, postgres_uid, postgres_gid)
        result["messages"].append(
            f"Set backup ownership to {postgres_uid}:{postgres_gid} (postgres)"
        )
    except OSError as exc:
        module.fail_json(msg=str(exc), **result)

    # --- Fix SELinux context on backup directory ---
    fix_selinux_context(backup_dir)

    # --- Verify ---
    if not os.path.isdir(backup_data_dir):
        module.fail_json(
            msg=f"Backup verification failed - {backup_data_dir} not found",
            **result
        )

    final_ver = read_pg_version(backup_data_dir)
    if final_ver not in compat:
        module.fail_json(
            msg=(
                f"Backup verification failed - backed up PG {final_ver or 'unknown'}, "
                f"expected {'/'.join(compat)}"
            ),
            **result
        )

    result["backup_pg_version"] = final_ver
    result["changed"] = True
    result["messages"].append(
        f"SUCCESS: Backed up PG {final_ver} data to {backup_data_dir}"
    )
    module.exit_json(**result)


# =========================================================================
# Restore logic
# =========================================================================

def run_restore(module, params, result):
    """Restore Pulp PostgreSQL data for rollback.

    Restores the PG 12/13 data from backup to the destination pgsql directory.
    The backup should contain only the data/ directory with compatible PG version.

    Args:
        module: AnsibleModule instance.
        params: Dict with 'backup_path', 'dest_path',
                and 'compatible_versions'.
        result: Mutable result dict.
    """
    backup_path = params["backup_path"]
    dest_path = params["dest_path"]
    compat = tuple(params["compatible_versions"])

    # --- Validate backup exists ---
    if not os.path.isdir(backup_path):
        module.fail_json(
            msg=f"Backup not found at {backup_path}",
            **result
        )

    # --- PostgreSQL requires UID 26 (postgres user) ---
    postgres_uid, postgres_gid = 26, 26

    # --- Find compatible PG data in backup ---
    backup_data_dir = os.path.join(backup_path, "data")
    backup_pg_ver = read_pg_version(backup_data_dir)
    result["backup_pg_version"] = backup_pg_ver or "unknown"

    if backup_pg_ver in compat:
        # Backup data/ has compatible PG version
        restore_source = backup_data_dir
        result["restore_mode"] = "direct"
        result["messages"].append(
            f"Backup contains PG {backup_pg_ver} data, restoring directly"
        )
    else:
        # Check for data_old in backup (legacy backup format)
        data_old_dir = find_data_old_dir(backup_path)
        if data_old_dir:
            old_pg_ver = read_pg_version(data_old_dir)
            if old_pg_ver in compat:
                restore_source = data_old_dir
                result["restore_mode"] = "data_old"
                result["messages"].append(
                    f"Using backup data_old (PG {old_pg_ver}) for restore"
                )
            else:
                module.fail_json(
                    msg=(
                        f"Backup data/ is PG {backup_pg_ver or 'unknown'} and "
                        f"data_old is PG {old_pg_ver or 'unknown'}. "
                        f"Cannot restore without PG {'/'.join(compat)} data."
                    ),
                    **result
                )
        else:
            module.fail_json(
                msg=(
                    f"Backup data/ is PG {backup_pg_ver or 'unknown'} "
                    f"and no data_old found. "
                    f"Cannot restore without PG {'/'.join(compat)} data."
                ),
                **result
            )

    # --- Check mode: report what would happen ---
    if module.check_mode:
        result["messages"].append("Check mode: no changes made")
        module.exit_json(**result)

    # --- Remove current destination pgsql directory ---
    if os.path.exists(dest_path):
        try:
            shutil.rmtree(dest_path)
            result["messages"].append(f"Removed existing data at {dest_path}")
        except (OSError, IOError) as exc:
            module.fail_json(
                msg=f"Failed to remove {dest_path}: {exc}",
                **result
            )

    # --- Restore: create pgsql/ with only data/ inside ---
    try:
        os.makedirs(dest_path, exist_ok=True)
        dest_data_dir = os.path.join(dest_path, "data")
        shutil.copytree(restore_source, dest_data_dir, symlinks=True)
    except (OSError, IOError, shutil.Error) as exc:
        module.fail_json(
            msg=f"Restore failed: {exc}",
            **result
        )

    # --- Fix ownership (postgres UID:GID = 26:26) ---
    try:
        fix_ownership(dest_path, postgres_uid, postgres_gid)
        result["messages"].append(
            f"Set ownership to {postgres_uid}:{postgres_gid} (postgres)"
        )
    except OSError as exc:
        module.fail_json(msg=str(exc), **result)

    # --- Fix SELinux context ---
    fix_selinux_context(dest_path)

    # --- Verify ---
    restored_data_dir = os.path.join(dest_path, "data")
    restored_ver = read_pg_version(restored_data_dir)
    result["restored_pg_version"] = restored_ver or "unknown"

    if restored_ver not in compat:
        module.fail_json(
            msg=(
                f"Restored data is PG {restored_ver or 'unknown'}, "
                f"expected {'/'.join(compat)}"
            ),
            **result
        )

    result["changed"] = True
    result["messages"].append(
        f"Restored PG {restored_ver} data to {dest_path}"
    )
    module.exit_json(**result)


# =========================================================================
# Module entry point
# =========================================================================

def run_module():
    """Ansible module entry point for Pulp PostgreSQL backup/restore."""
    module_args = dict(
        action=dict(
            type="str", required=True,
            choices=["backup", "restore"]
        ),
        # Common parameters
        dest_path=dict(type="str", required=True),
        compatible_versions=dict(
            type="list", elements="str", required=False,
            default=list(COMPATIBLE_PG_VERSIONS)
        ),
        # Backup-specific parameters
        src_path=dict(type="str", required=False, default=""),
        backup_dir=dict(type="str", required=False, default=""),
        # Restore-specific parameters
        backup_path=dict(type="str", required=False, default=""),
    )

    result = dict(
        changed=False,
        skipped=False,
        restore_mode="",
        source_pg_version="",
        backup_pg_version="",
        restored_pg_version="",
        messages=[],
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[
            ("action", "backup", ["src_path", "dest_path", "backup_dir"]),
            ("action", "restore", ["backup_path", "dest_path"]),
        ],
    )

    action = module.params["action"]

    if action == "backup":
        run_backup(module, module.params, result)
    elif action == "restore":
        run_restore(module, module.params, result)


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
