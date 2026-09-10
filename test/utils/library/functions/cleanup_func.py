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
Utils Domain - Cleanup Verification Functions.

Functions to verify cleanup operations for log collection and install_os.
"""

import os
from datetime import datetime, timedelta


def check_old_log_bundles_removed(host, output_path, retention_days=7):
    """Check if old log bundles are removed based on retention policy.

    Args:
        host: Testinfra host fixture.
        output_path: Path to utils output directory.
        retention_days: Number of days to retain log bundles (default: 7).

    Returns:
        dict: {
            "success": bool,
            "old_bundles": list of old bundle paths still present,
            "current_bundles": list of current bundle paths,
            "retention_days": int,
            "error": str or None
        }
    """
    collect_path = f"{output_path}/collect"
    result = {
        "success": True,
        "old_bundles": [],
        "current_bundles": [],
        "retention_days": retention_days,
        "error": None,
    }

    try:
        # Check if collect directory exists
        check_cmd = f"test -d {collect_path} && echo 'exists' || echo 'missing'"
        check_result = host.run(check_cmd)
        if "missing" in check_result.stdout:
            # No collect directory means cleanup was successful
            return result

        # Find all log bundles
        find_cmd = f"find {collect_path} -name 'omnia_logs_*.tar.gz' -type f 2>/dev/null"
        find_result = host.run(find_cmd)

        if find_result.rc != 0:
            result["error"] = f"Failed to find log bundles: {find_result.stderr}"
            result["success"] = False
            return result

        bundles = [b.strip() for b in find_result.stdout.strip().split('\n') if b.strip()]

        # Check age of each bundle
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        for bundle in bundles:
            # Get file modification time
            stat_cmd = f"stat -c %Y {bundle} 2>/dev/null"
            stat_result = host.run(stat_cmd)

            if stat_result.rc == 0:
                try:
                    mtime = int(stat_result.stdout.strip())
                    bundle_date = datetime.fromtimestamp(mtime)

                    if bundle_date < cutoff_date:
                        result["old_bundles"].append(bundle)
                    else:
                        result["current_bundles"].append(bundle)
                except (ValueError, OSError):
                    result["current_bundles"].append(bundle)
            else:
                result["current_bundles"].append(bundle)

        # Success if no old bundles remain
        result["success"] = len(result["old_bundles"]) == 0

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def check_empty_log_dirs_removed(host, output_path):
    """Check if empty log collection directories are removed.

    Args:
        host: Testinfra host fixture.
        output_path: Path to utils output directory.

    Returns:
        dict: {
            "success": bool,
            "empty_dirs": list of empty directories still present,
            "error": str or None
        }
    """
    collect_path = f"{output_path}/collect"
    result = {
        "success": True,
        "empty_dirs": [],
        "error": None,
    }

    try:
        # Check if collect directory exists
        check_cmd = f"test -d {collect_path} && echo 'exists' || echo 'missing'"
        check_result = host.run(check_cmd)
        if "missing" in check_result.stdout:
            return result

        # Find empty directories (omnia_logs_* directories without content)
        find_cmd = f"find {collect_path} -type d -name 'omnia_logs_*' -empty 2>/dev/null"
        find_result = host.run(find_cmd)

        if find_result.rc == 0 and find_result.stdout.strip():
            result["empty_dirs"] = [d.strip() for d in find_result.stdout.strip().split('\n') if d.strip()]
            result["success"] = len(result["empty_dirs"]) == 0

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def check_temp_log_dirs_cleaned(host, output_path):
    """Check if temporary log collection directories (k8s, slurm) are cleaned.

    Args:
        host: Testinfra host fixture.
        output_path: Path to utils output directory.

    Returns:
        dict: {
            "success": bool,
            "temp_dirs_status": dict mapping dir name to exists status,
            "error": str or None
        }
    """
    collect_path = f"{output_path}/collect"
    temp_dirs = ["k8s", "slurm"]
    result = {
        "success": True,
        "temp_dirs_status": {},
        "error": None,
    }

    try:
        for temp_dir in temp_dirs:
            dir_path = f"{collect_path}/{temp_dir}"
            check_cmd = f"test -d {dir_path} && echo 'exists' || echo 'cleaned'"
            check_result = host.run(check_cmd)

            exists = "exists" in check_result.stdout
            result["temp_dirs_status"][temp_dir] = "exists" if exists else "cleaned"

            # Temp dirs should be cleaned (not exist or be empty)
            if exists:
                # Check if directory has content
                content_cmd = f"ls -A {dir_path} 2>/dev/null | head -1"
                content_result = host.run(content_cmd)
                if content_result.stdout.strip():
                    result["success"] = False

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def check_install_os_temp_dir_removed(host):
    """Check if /tmp/install_os directory is removed.

    Args:
        host: Testinfra host fixture.

    Returns:
        dict: {
            "success": bool,
            "path": str,
            "exists": bool,
            "error": str or None
        }
    """
    temp_path = "/tmp/install_os"
    result = {
        "success": True,
        "path": temp_path,
        "exists": False,
        "error": None,
    }

    try:
        check_cmd = f"test -d {temp_path} && echo 'exists' || echo 'removed'"
        check_result = host.run(check_cmd)

        result["exists"] = "exists" in check_result.stdout
        result["success"] = not result["exists"]

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def check_install_os_nfs_unmounted(host):
    """Check if /tmp/install_os_nfs is unmounted and removed.

    Args:
        host: Testinfra host fixture.

    Returns:
        dict: {
            "success": bool,
            "path": str,
            "mounted": bool,
            "exists": bool,
            "error": str or None
        }
    """
    nfs_path = "/tmp/install_os_nfs"
    result = {
        "success": True,
        "path": nfs_path,
        "mounted": False,
        "exists": False,
        "error": None,
    }

    try:
        # Check if mounted using mountpoint command (more reliable)
        mount_cmd = f"mountpoint -q {nfs_path} 2>/dev/null && echo 'mounted' || echo 'not_mounted'"
        mount_result = host.run(mount_cmd)
        result["mounted"] = "mounted" in mount_result.stdout

        # Check if directory exists
        check_cmd = f"test -d {nfs_path} && echo 'exists' || echo 'removed'"
        check_result = host.run(check_cmd)
        result["exists"] = "exists" in check_result.stdout

        # Success if not mounted and not exists
        result["success"] = not result["mounted"] and not result["exists"]

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def check_install_os_credentials_removed(host, input_path):
    """Check if install_os credential files are removed.

    Args:
        host: Testinfra host fixture.
        input_path: Path to utils input directory.

    Returns:
        dict: {
            "success": bool,
            "results": list of {path, removed, query_error},
            "error": str or None
        }
    """
    credential_files = [
        f"{input_path}/install_os_credentials.yml",
        f"{input_path}/.install_os_credentials_key",
    ]
    result = {
        "success": True,
        "results": [],
        "error": None,
    }

    try:
        for cred_file in credential_files:
            item = {
                "path": cred_file,
                "removed": True,
                "query_error": None,
            }

            check_cmd = f"test -f {cred_file} && echo 'exists' || echo 'removed'"
            check_result = host.run(check_cmd)

            if check_result.rc != 0:
                item["query_error"] = check_result.stderr
            else:
                item["removed"] = "removed" in check_result.stdout

            result["results"].append(item)

            if not item["removed"]:
                result["success"] = False

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def check_all_logs_cleaned(host, output_path):
    """Check if all log collection artifacts are cleaned.

    Args:
        host: Testinfra host fixture.
        output_path: Path to utils output directory.

    Returns:
        dict: {
            "success": bool,
            "bundles_cleaned": bool,
            "empty_dirs_cleaned": bool,
            "temp_dirs_cleaned": bool,
            "details": dict,
            "error": str or None
        }
    """
    result = {
        "success": True,
        "bundles_cleaned": True,
        "empty_dirs_cleaned": True,
        "temp_dirs_cleaned": True,
        "details": {},
        "error": None,
    }

    try:
        # Check old bundles
        bundles_result = check_old_log_bundles_removed(host, output_path)
        result["bundles_cleaned"] = bundles_result["success"]
        result["details"]["bundles"] = bundles_result

        # Check empty dirs
        empty_result = check_empty_log_dirs_removed(host, output_path)
        result["empty_dirs_cleaned"] = empty_result["success"]
        result["details"]["empty_dirs"] = empty_result

        # Check temp dirs
        temp_result = check_temp_log_dirs_cleaned(host, output_path)
        result["temp_dirs_cleaned"] = temp_result["success"]
        result["details"]["temp_dirs"] = temp_result

        result["success"] = all([
            result["bundles_cleaned"],
            result["empty_dirs_cleaned"],
            result["temp_dirs_cleaned"],
        ])

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def check_all_install_os_cleaned(host, input_path):
    """Check if all install_os artifacts are cleaned.

    Args:
        host: Testinfra host fixture.
        input_path: Path to utils input directory.

    Returns:
        dict: {
            "success": bool,
            "temp_dir_cleaned": bool,
            "nfs_cleaned": bool,
            "credentials_cleaned": bool,
            "details": dict,
            "error": str or None
        }
    """
    result = {
        "success": True,
        "temp_dir_cleaned": True,
        "nfs_cleaned": True,
        "credentials_cleaned": True,
        "details": {},
        "error": None,
    }

    try:
        # Check temp dir
        temp_result = check_install_os_temp_dir_removed(host)
        result["temp_dir_cleaned"] = temp_result["success"]
        result["details"]["temp_dir"] = temp_result

        # Check NFS - skip if NFS mount was never created (install_os not run)
        nfs_path = "/tmp/install_os_nfs"
        nfs_check_cmd = f"test -d {nfs_path} || mount | grep -q '{nfs_path}'"
        nfs_check_result = host.run(nfs_check_cmd)

        if nfs_check_result.rc != 0:
            # NFS mount was never created, consider it cleaned
            result["nfs_cleaned"] = True
            result["details"]["nfs"] = {
                "success": True,
                "path": nfs_path,
                "mounted": False,
                "exists": False,
                "skipped": True,
                "reason": "NFS mount was never created (install_os not run)"
            }
        else:
            # NFS mount exists, check if it was cleaned
            nfs_result = check_install_os_nfs_unmounted(host)
            result["nfs_cleaned"] = nfs_result["success"]
            result["details"]["nfs"] = nfs_result

        # Check credentials (note: credentials may be intentionally kept)
        creds_result = check_install_os_credentials_removed(host, input_path)
        result["credentials_cleaned"] = creds_result["success"]
        result["details"]["credentials"] = creds_result

        # Success requires temp_dir and nfs to be cleaned
        # Credentials cleanup is optional (controlled by cleanup_credentials flag)
        result["success"] = result["temp_dir_cleaned"] and result["nfs_cleaned"]

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def check_setup_output_dir_exists(host, output_path):
    """Check if setup created the output directory.

    Args:
        host: Testinfra host fixture.
        output_path: Path to utils output directory.

    Returns:
        dict: {
            "success": bool,
            "path": str,
            "exists": bool,
            "error": str or None
        }
    """
    result = {
        "success": False,
        "path": output_path,
        "exists": False,
        "error": None,
    }

    try:
        check_cmd = f"test -d {output_path} && echo 'exists' || echo 'missing'"
        check_result = host.run(check_cmd)

        result["exists"] = "exists" in check_result.stdout
        result["success"] = result["exists"]

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def check_setup_input_dir_exists(host, input_path):
    """Check if setup created the input directory.

    Args:
        host: Testinfra host fixture.
        input_path: Path to utils input directory.

    Returns:
        dict: {
            "success": bool,
            "path": str,
            "exists": bool,
            "error": str or None
        }
    """
    result = {
        "success": False,
        "path": input_path,
        "exists": False,
        "error": None,
    }

    try:
        check_cmd = f"test -d {input_path} && echo 'exists' || echo 'missing'"
        check_result = host.run(check_cmd)

        result["exists"] = "exists" in check_result.stdout
        result["success"] = result["exists"]

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result
