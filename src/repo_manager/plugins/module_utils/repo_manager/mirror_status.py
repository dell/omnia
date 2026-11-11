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

"""
Mirror status management for multi-catalog repo_manager.

Handles:
- pulp_mirror_index.json: Global mirror index with composite key hashes
- Incremental mirroring with hash-based change detection
- Rerun filtering based on status

All catalog keys are expected in lowercase (identifier, name).
"""

import os
import json
import tempfile
from datetime import datetime, timezone

MIRROR_INDEX_SCHEMA_VERSION = 3
REPOSITORY_SYNC_STATES = frozenset(("pending", "ready", "failed"))


# ---------------------------------------------------------------------------
# Mirror Index (pulp_mirror_index.json)
# ---------------------------------------------------------------------------

def _empty_mirror_index():
    """Return empty mirror index structure."""
    return {
        "MirrorIndex": {
            "schema_version": MIRROR_INDEX_SCHEMA_VERSION,
            "timestamp": "",
            "summary": {
                "total_unique": 0,
                "mirrored": 0,
                "failed": 0,
                "pending": 0
            },
            "packages": {},
            "repositories": {}
        }
    }


def migrate_mirror_index(mirror_data, global_index, logger):
    """Migrate legacy name-keyed entries to composite-hash keys in memory.

    Existing status is preserved when its stored hash matches the current
    global package index.  Entries no longer present in the catalog are retained
    under their stored hash so cleanup can still remove them.  Identities that
    were previously collapsed by a name collision remain absent and are
    naturally scheduled as new work by change detection.

    Returns:
        bool: ``True`` when the in-memory structure changed.
    """
    mirror_root = mirror_data.setdefault("MirrorIndex", {})
    packages = mirror_root.setdefault("packages", {})
    mirror_root.setdefault("repositories", {})
    schema_version = mirror_root.get("schema_version", 1)

    already_current = (
        schema_version == MIRROR_INDEX_SCHEMA_VERSION
        and isinstance(mirror_root["repositories"], dict)
        and all(key == entry.get("hash") and entry.get("package_name")
                for key, entry in packages.items())
    )
    if already_current:
        return False

    global_by_hash = {
        composite_hash: pkg_info
        for arch_packages in global_index.values()
        for composite_hash, pkg_info in arch_packages.items()
    }
    migrated = {}
    for legacy_key, legacy_entry in packages.items():
        if not isinstance(legacy_entry, dict):
            logger.warning("Skipping malformed mirror-index entry '%s'", legacy_key)
            continue

        entry = dict(legacy_entry)
        composite_hash = entry.get("hash", "")
        current = global_by_hash.get(composite_hash)
        if current:
            entry.update({
                "package_name": current["package_name"],
                "type": current["type"],
                "version": current["version"],
                "arch": current["arch"],
                "hash": composite_hash,
                "source": current.get("group_name", entry.get("source", "")),
                "repo_name": current.get("repo_name", ""),
                "catalogs": sorted(set(
                    entry.get("catalogs", []) + current.get("catalogs", [])
                )),
            })
        else:
            entry.setdefault("package_name", legacy_key)

        # Legacy files produced by Repo Manager already contain a composite
        # hash. Preserve unmatched/stale entries by that hash for cleanup.
        identity_key = composite_hash or f"legacy:{legacy_key}"
        migrated[identity_key] = entry

    mirror_root["packages"] = migrated
    mirror_root["schema_version"] = MIRROR_INDEX_SCHEMA_VERSION
    logger.info(
        "Migrated mirror index from schema %s to %s (%d entries)",
        schema_version, MIRROR_INDEX_SCHEMA_VERSION, len(migrated)
    )
    return True

def load_mirror_index(mirror_index_path, logger):
    """Load the global mirror index from disk with corrupted JSON handling.

    Args:
        mirror_index_path (str): Path to pulp_mirror_index.json.
        logger: Logger instance.

    Returns:
        dict: Mirror index data, or an empty structure when the file is absent.

    Raises:
        ValueError: The existing state is corrupt or structurally invalid.
        OSError: The existing state cannot be read.
    """
    if not os.path.isfile(mirror_index_path):
        logger.info("Mirror index not found at %s, starting fresh", mirror_index_path)
        return _empty_mirror_index()

    try:
        with open(mirror_index_path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)

        mirror_root = data.get("MirrorIndex") if isinstance(data, dict) else None
        repository_states = (
            mirror_root.get("repositories", {})
            if isinstance(mirror_root, dict) else {}
        )
        if (
                not isinstance(data, dict)
                or not isinstance(mirror_root, dict)
                or not isinstance(
                    mirror_root.get("packages", {}), dict
                )
                or not isinstance(
                    repository_states, dict
                )
                or any(
                    not isinstance(repo_name, str)
                    or not isinstance(state, dict)
                    or state.get("status") not in REPOSITORY_SYNC_STATES
                    for repo_name, state in repository_states.items()
                )):
            raise ValueError("Mirror index has an invalid structure")
        mirror_root.setdefault("repositories", {})
        logger.info("Loaded mirror index from %s with %d packages",
                    mirror_index_path,
                    len(data["MirrorIndex"].get("packages", {})))
        return data
    except (json.JSONDecodeError, ValueError) as error:
        logger.error("Mirror index file is corrupted")
        raise ValueError("Mirror index file is corrupted") from error
    except OSError:
        logger.error("Unable to load the mirror index")
        raise


def save_mirror_index(mirror_index_path, mirror_data, logger):
    """Save the global mirror index to disk using atomic write.

    Args:
        mirror_index_path (str): Path to pulp_mirror_index.json.
        mirror_data (dict): Mirror index data to save.
        logger: Logger instance.
    """
    os.makedirs(os.path.dirname(mirror_index_path), exist_ok=True)

    # Update timestamp
    mirror_data["MirrorIndex"]["schema_version"] = MIRROR_INDEX_SCHEMA_VERSION
    mirror_data["MirrorIndex"]["timestamp"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")

    # Update summary
    packages = mirror_data["MirrorIndex"].get("packages", {})
    summary = {
        "total_unique": len(packages),
        "mirrored": sum(1 for p in packages.values() if p.get("status") == "mirrored"),
        "failed": sum(1 for p in packages.values() if p.get("status") == "failed"),
        "pending": sum(1 for p in packages.values() if p.get("status") == "pending"),
    }
    mirror_data["MirrorIndex"]["summary"] = summary

    descriptor, temp_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(mirror_index_path)}.",
        suffix=".tmp",
        dir=os.path.dirname(mirror_index_path),
    )
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as fh:
            json.dump(mirror_data, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_path, mirror_index_path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    logger.info("Saved mirror index to %s: %d packages (mirrored=%d, failed=%d, pending=%d)",
                mirror_index_path, summary["total_unique"],
                summary["mirrored"], summary["failed"], summary["pending"])


def repositories_requiring_retry(mirror_data):
    """Return repositories whose interrupted or failed sync must be retried."""
    repositories = mirror_data.get("MirrorIndex", {}).get("repositories", {})
    if not isinstance(repositories, dict):
        raise ValueError("Mirror index repository state is invalid")
    return {
        repo_name
        for repo_name, state in repositories.items()
        if isinstance(state, dict)
        and state.get("status") in ("pending", "failed")
    }


def update_repository_sync_state(
        mirror_data, repo_name, status, version_href=None, policy=None):
    """Update one exact repository checkpoint in the mirror index.

    The last confirmed version is retained while a new sync is pending or has
    failed.  Raw Pulp errors are deliberately not persisted in this shared
    state file.
    """
    if status not in REPOSITORY_SYNC_STATES:
        raise ValueError("Unsupported repository synchronization state")
    if not isinstance(repo_name, str) or not repo_name:
        raise ValueError("Repository name is required")

    mirror_root = mirror_data.setdefault("MirrorIndex", {})
    repositories = mirror_root.setdefault("repositories", {})
    entry = repositories.setdefault(repo_name, {})
    entry["status"] = status
    entry["retry_required"] = status in ("pending", "failed")
    if version_href is not None:
        entry["version_href"] = version_href
    else:
        entry.setdefault("version_href", "")
    if policy is not None:
        entry["policy"] = policy
    else:
        entry.setdefault("policy", "")
    if status == "ready":
        entry["last_successful_sync"] = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    else:
        entry.setdefault("last_successful_sync", "")


def remove_repository_sync_state(mirror_data, repo_name):
    """Remove one repository checkpoint and report whether it existed."""
    repositories = mirror_data.get("MirrorIndex", {}).get("repositories", {})
    if not isinstance(repositories, dict):
        raise ValueError("Mirror index repository state is invalid")
    return repositories.pop(repo_name, None) is not None


def mark_package_entries_pending(mirror_data, composite_hashes):
    """Mark existing exact package identities pending and return the count."""
    packages = mirror_data.get("MirrorIndex", {}).get("packages", {})
    if not isinstance(packages, dict):
        raise ValueError("Mirror index package state is invalid")
    updated = 0
    for composite_hash in set(composite_hashes):
        entry = packages.get(composite_hash)
        if not isinstance(entry, dict):
            continue
        entry["status"] = "pending"
        entry["error"] = ""
        updated += 1
    return updated


def save_global_package_index(global_index_path, global_index, logger):
    """Save global package index to JSON file for reference.

    Args:
        global_index_path (str): Path to global_package_index.json.
        global_index (dict): Global package index from build_global_package_index.
        logger: Logger instance.
    """
    os.makedirs(os.path.dirname(global_index_path), exist_ok=True)

    # Convert OrderedDict to regular dict and create a more readable format
    output_data = {
        "GlobalPackageIndex": {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": {},
            "packages_by_arch": {}
        }
    }

    total_packages = 0
    for arch, packages in global_index.items():
        arch_packages = []
        for _composite_hash, pkg_info in packages.items():
            arch_packages.append({
                "package_name": pkg_info["package_name"],
                "type": pkg_info["type"],
                "version": pkg_info["version"],
                "arch": pkg_info["arch"],
                "hash": pkg_info["hash"],
                "group_name": pkg_info["group_name"],
                "repo_name": pkg_info.get("repo_name", ""),
                "catalog_name": pkg_info["catalog_name"],
                "catalogs": pkg_info["catalogs"],
                "source_catalog_file": pkg_info.get("source_catalog_file", "")
            })

        output_data["GlobalPackageIndex"]["packages_by_arch"][arch] = arch_packages
        output_data["GlobalPackageIndex"]["summary"][arch] = len(arch_packages)
        total_packages += len(arch_packages)

    output_data["GlobalPackageIndex"]["summary"]["total"] = total_packages

    existing_mode = (
        os.stat(global_index_path).st_mode & 0o777
        if os.path.exists(global_index_path) else None
    )
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(global_index_path)}.",
        suffix=".tmp",
        dir=os.path.dirname(global_index_path),
    )
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as fh:
            json.dump(output_data, fh, indent=2, sort_keys=False)
            fh.flush()
            os.fsync(fh.fileno())
        if existing_mode is not None:
            os.chmod(temporary_path, existing_mode)
        os.replace(temporary_path, global_index_path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)

    logger.info("Saved global package index to %s: %d total packages across %d architectures",
                global_index_path, total_packages, len(global_index))


def update_mirror_index_entry(mirror_data, package_name, pkg_type, version, arch,
                               composite_hash, source, catalogs, status, error="", repo_name=""):
    """Update or create an entry in the mirror index.

    Args:
        mirror_data (dict): Mirror index data (modified in place).
        package_name (str): Package name.
        pkg_type (str): Package type.
        version (str): Package version.
        arch (str): Architecture.
        composite_hash (str): Composite key hash.
        source (str): Source group name.
        catalogs (list[str]): List of catalog identifiers referencing this package.
        status (str): Status (mirrored/failed/pending).
        error (str): Error message if failed.
        repo_name (str): Repository name where package is sourced from.
    """
    packages = mirror_data["MirrorIndex"].setdefault("packages", {})
    if not composite_hash:
        raise ValueError(
            f"Composite hash is required for mirror-index entry '{package_name}'"
        )

    if composite_hash in packages:
        # Update existing entry
        entry = packages[composite_hash]
        entry.update({
            "package_name": package_name,
            "type": pkg_type,
            "version": version,
            "arch": arch,
            "hash": composite_hash,
            "source": source,
            "repo_name": repo_name,
        })
        entry["status"] = status
        if status == "mirrored":
            entry["last_mirrored"] = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        entry["error"] = error
        # Merge catalogs
        existing_catalogs = set(entry.get("catalogs", []))
        existing_catalogs.update(catalogs)
        entry["catalogs"] = sorted(existing_catalogs)
    else:
        # Create new entry
        packages[composite_hash] = {
            "package_name": package_name,
            "type": pkg_type,
            "version": version,
            "arch": arch,
            "hash": composite_hash,
            "source": source,
            "repo_name": repo_name,
            "status": status,
            "last_mirrored": (
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if status == "mirrored" else ""
            ),
            "catalogs": sorted(set(catalogs)),
            "error": error
        }


def find_mirror_entry(mirror_data, package_name, pkg_type, arch):
    """Find one exact mirror entry for a status.csv package identity.

    Image rows include the tag in ``package_name`` while mirror entries keep the
    image name and tag/version in separate fields.  Type and architecture
    disambiguate identities such as ``papi`` being both an RPM and a tarball.

    Returns:
        tuple[str, dict] | tuple[None, None]: Composite key and entry.
    """
    packages = mirror_data.get("MirrorIndex", {}).get("packages", {})
    candidates = []
    for identity_key, entry in packages.items():
        if entry.get("type") != pkg_type or entry.get("arch") != arch:
            continue

        entry_name = entry.get("package_name", "")
        if pkg_type == "image":
            version = entry.get("version", "")
            display_name = f"{entry_name}:{version}" if version else entry_name
            if package_name not in (entry_name, display_name):
                continue
        elif package_name != entry_name:
            continue
        candidates.append((identity_key, entry))

    if len(candidates) == 1:
        return candidates[0]
    return None, None


# ---------------------------------------------------------------------------
# Incremental Mirroring: Hash-Based Change Detection
# ---------------------------------------------------------------------------

def detect_package_changes(global_index, mirror_data, arch, logger):
    """Detect which packages need to be mirrored, re-mirrored, or skipped.

    Compares the global package index against the existing pulp_mirror_index.json.

    Args:
        global_index (dict): Output from build_global_package_index, for one arch.
        mirror_data (dict): Loaded mirror index data.
        arch (str): Architecture being processed.
        logger: Logger instance.

    Returns:
        dict: {
            "mirror": list of package info dicts (new packages),
            "re_mirror": list of package info dicts (changed composite key),
            "skip": list of package info dicts (unchanged),
            "retry": list of package info dicts (previously failed),
        }
    """
    existing_packages = mirror_data.get("MirrorIndex", {}).get("packages", {})

    result = {"mirror": [], "re_mirror": [], "skip": [], "retry": []}

    arch_index = global_index.get(arch, {})
    for composite_hash, pkg_info in arch_index.items():
        pkg_name = pkg_info["package_name"]
        existing = existing_packages.get(composite_hash)

        if existing is None:
            # New package - needs mirroring
            result["mirror"].append(pkg_info)
            logger.info("MIRROR (new): %s (%s) for arch %s",
                         pkg_name, pkg_info["type"], arch)
        elif existing.get("status") == "failed":
            # Previously failed - retry
            result["retry"].append(pkg_info)
            logger.info("RETRY (failed): %s (%s) for arch %s",
                         pkg_name, pkg_info["type"], arch)
        elif existing.get("status") == "pending":
            # Still pending (never completed) - retry
            result["retry"].append(pkg_info)
            logger.info("RETRY (pending): %s (%s) for arch %s",
                         pkg_name, pkg_info["type"], arch)
        elif existing.get("hash") != composite_hash:
            # Composite key changed - re-mirror
            result["re_mirror"].append(pkg_info)
            logger.info("RE-MIRROR (changed): %s (%s) for arch %s, "
                         "old_hash=%s, new_hash=%s",
                         pkg_name, pkg_info["type"], arch,
                         existing.get("hash", ""), composite_hash)
        else:
            # Unchanged and mirrored - skip
            result["skip"].append(pkg_info)
            logger.info("SKIP (unchanged): %s (%s) for arch %s",
                         pkg_name, pkg_info["type"], arch)

    logger.info("Change detection for arch %s: mirror=%d, re_mirror=%d, retry=%d, skip=%d",
                arch, len(result["mirror"]), len(result["re_mirror"]),
                len(result["retry"]), len(result["skip"]))
    return result


def filter_tasks_for_processing(change_results, logger):
    """Filter the change detection results to get only packages that need processing.

    Args:
        change_results (dict): Output from detect_package_changes.
        logger: Logger instance.

    Returns:
        list: List of package info dicts that need to be downloaded/mirrored.
    """
    to_process = (
        change_results["mirror"] +
        change_results["re_mirror"] +
        change_results["retry"]
    )
    logger.info("Total packages to process: %d (new=%d, changed=%d, retry=%d)",
                len(to_process),
                len(change_results["mirror"]),
                len(change_results["re_mirror"]),
                len(change_results["retry"]))
    return to_process
