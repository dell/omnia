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
- Per-catalog status JSON files
- CSV status files with catalog_name column (group_status.csv, package_status.csv)
- Incremental mirroring with hash-based change detection
- Rerun filtering based on status

All catalog keys are expected in lowercase (identifier, name).
"""

import os
import json
from datetime import datetime, timezone

from ansible.module_utils.repo_manager.config import ARCH_SUFFIXES

MIRROR_INDEX_SCHEMA_VERSION = 2


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
            "packages": {}
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
    schema_version = mirror_root.get("schema_version", 1)

    already_current = (
        schema_version == MIRROR_INDEX_SCHEMA_VERSION
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
        dict: Mirror index data, or empty structure if file doesn't exist or is corrupted.
    """
    if not os.path.isfile(mirror_index_path):
        logger.info("Mirror index not found at %s, starting fresh", mirror_index_path)
        return _empty_mirror_index()

    try:
        with open(mirror_index_path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)

        logger.info("Loaded mirror index from %s with %d packages",
                    mirror_index_path,
                    len(data.get("MirrorIndex", {}).get("packages", {})))
        return data
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Mirror index file corrupted at {mirror_index_path}: {e}")
        logger.info("Starting fresh with empty mirror index")
        return _empty_mirror_index()
    except Exception as e:
        logger.error(f"Error loading mirror index from {mirror_index_path}: {e}")
        logger.info("Starting fresh with empty mirror index")
        return _empty_mirror_index()


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

    # Atomic write: write to temp file then replace
    # Use unique temp filename per process to avoid race conditions in parallel execution
    temp_path = f"{mirror_index_path}.tmp.{os.getpid()}"
    with open(temp_path, 'w', encoding='utf-8') as fh:
        json.dump(mirror_data, fh, indent=2)
    os.replace(temp_path, mirror_index_path)

    logger.info("Saved mirror index to %s: %d packages (mirrored=%d, failed=%d, pending=%d)",
                mirror_index_path, summary["total_unique"],
                summary["mirrored"], summary["failed"], summary["pending"])


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

    with open(global_index_path, 'w', encoding='utf-8') as fh:
        json.dump(output_data, fh, indent=2, sort_keys=False)

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


# ---------------------------------------------------------------------------
# Per-Catalog Status Files
# ---------------------------------------------------------------------------

def load_catalog_status(status_path, logger):
    """Load a per-catalog status JSON file.

    Args:
        status_path (str): Path to the catalog status JSON file.
        logger: Logger instance.

    Returns:
        dict: Catalog status data or empty structure.
    """
    if not os.path.isfile(status_path):
        return {
            "MirrorStatus": {
                "catalog": "",
                "identifier": "",
                "timestamp": "",
                "summary": {"total": 0, "mirrored": 0, "failed": 0, "skipped": 0},
                "packages": {}
            }
        }

    with open(status_path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def save_catalog_status(status_path, catalog_status, logger):
    """Save a per-catalog status JSON file.

    Args:
        status_path (str): Path to save the catalog status file.
        catalog_status (dict): Catalog status data.
        logger: Logger instance.
    """
    os.makedirs(os.path.dirname(status_path), exist_ok=True)

    # Update timestamp
    catalog_status["MirrorStatus"]["timestamp"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")

    # Update summary
    packages = catalog_status["MirrorStatus"].get("packages", {})
    catalog_status["MirrorStatus"]["summary"] = {
        "total": len(packages),
        "mirrored": sum(1 for p in packages.values() if p.get("status") == "mirrored"),
        "failed": sum(1 for p in packages.values() if p.get("status") == "failed"),
        "skipped": sum(1 for p in packages.values() if p.get("status") == "skipped"),
    }

    with open(status_path, 'w', encoding='utf-8') as fh:
        json.dump(catalog_status, fh, indent=2)

    logger.info("Saved catalog status to %s", status_path)


def update_catalog_status_entry(catalog_status, package_name, pkg_type, version,
                                 arch, composite_hash, status, error=""):
    """Update a package entry in a per-catalog status file.

    Args:
        catalog_status (dict): Catalog status data (modified in place).
        package_name (str): Package name.
        pkg_type (str): Package type.
        version (str): Package version.
        arch (str): Target architecture.
        composite_hash (str): Composite key hash.
        status (str): Status (mirrored/failed/skipped).
        error (str): Error message if failed.
    """
    packages = catalog_status["MirrorStatus"].setdefault("packages", {})
    packages[composite_hash] = {
        "package_name": package_name,
        "type": pkg_type,
        "version": version,
        "arch": arch,
        "hash": composite_hash,
        "status": status,
        "last_mirrored": (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if status == "mirrored" else ""
        ),
        "error": error
    }


# ---------------------------------------------------------------------------
# CSV Status Files
# ---------------------------------------------------------------------------

PACKAGE_STATUS_CSV_HEADER = "name,type,repo_name,status,catalog_name\n"
GROUP_STATUS_CSV_HEADER = "name,status\n"


def write_package_status_csv(csv_path, entries, logger):
    """Write package status CSV file with catalog_name column.

    Args:
        csv_path (str): Path to the package_status.csv file.
        entries (list[dict]): List of dicts with keys: name, type, repo_name, status, catalog_name.
        logger: Logger instance.
    """
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    with open(csv_path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(PACKAGE_STATUS_CSV_HEADER)
        for entry in entries:
            line = f"{entry.get('name', '')},{entry.get('type', '')}," \
                   f"{entry.get('repo_name', '')},{entry.get('status', '')}," \
                   f"{entry.get('catalog_name', '')}\n"
            fh.write(line)

    logger.info("Wrote package status CSV to %s with %d entries", csv_path, len(entries))


def write_group_status_csv(csv_path, groups, logger):
    """Write group status CSV file.

    Args:
        csv_path (str): Path to the group_status.csv file.
        groups (list[dict]): List of dicts with keys: name, status.
        logger: Logger instance.
    """
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    with open(csv_path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(GROUP_STATUS_CSV_HEADER)
        for group in groups:
            fh.write(f"{group.get('name', '')},{group.get('status', '')}\n")

    logger.info("Wrote group status CSV to %s with %d entries", csv_path, len(groups))


# ---------------------------------------------------------------------------
# Status File Generation (Post-Execution)
# ---------------------------------------------------------------------------

def generate_multi_catalog_status(global_index, mirror_data, catalogs,
                                   status_base_dir, logger):
    """Generate all status files after multi-catalog processing.

    Creates:
    - Updated pulp_mirror_index.json (already updated during processing)
    - Per-catalog status JSON files
    - Per-catalog CSV status files (group_status.csv, package_status.csv)

    Args:
        global_index (dict): Global package index.
        mirror_data (dict): Mirror index data (already updated with results).
        catalogs (list[dict]): List of loaded catalogs (lowercase keys).
        status_base_dir (str): Base directory for status files.
        logger: Logger instance.
    """
    existing_packages = mirror_data.get("MirrorIndex", {}).get("packages", {})

    for catalog in catalogs:
        catalog_id = catalog["identifier"]
        catalog_name = catalog["name"]
        catalog_file = catalog.get("_source_file", "")

        # Create per-catalog status
        catalog_status = {
            "MirrorStatus": {
                "catalog": catalog_file,
                "identifier": catalog_id,
                "timestamp": "",
                "summary": {},
                "packages": {}
            }
        }

        # Populate packages for this catalog from the current global index so
        # same-name tags, types, and architectures remain separate.
        for arch, arch_index in global_index.items():
            for composite_hash, pkg_info in arch_index.items():
                if catalog_id not in pkg_info.get("catalogs", []):
                    continue
                mirror_entry = existing_packages.get(composite_hash, {})
                update_catalog_status_entry(
                    catalog_status,
                    pkg_info["package_name"],
                    pkg_info.get("type", ""),
                    pkg_info.get("version", ""),
                    arch,
                    composite_hash,
                    mirror_entry.get("status", "pending"),
                    mirror_entry.get("error", "")
                )

        # Save per-catalog status JSON
        # Derive OS type from catalog identifier (e.g., "omnia-services-rhel-10-0" -> "rhel")
        os_type = "rhel"  # default
        for part in catalog_id.split("-"):
            if part in ("rhel"):
                os_type = part
                break

        catalog_status_dir = os.path.join(status_base_dir, "mirror_status", os_type)
        catalog_status_file = os.path.join(
            catalog_status_dir,
            f"{catalog_id.replace('-', '_')}_catalog_status.json"
        )
        save_catalog_status(catalog_status_file, catalog_status, logger)

        # Generate CSV status files per arch/group
        for arch in ARCH_SUFFIXES:
            arch_index = global_index.get(arch, {})
            # Collect groups and their packages for this catalog
            groups_packages = {}  # group_name -> list of pkg entries
            for _hash, pkg_info in arch_index.items():
                if catalog_id in pkg_info.get("catalogs", []):
                    group = pkg_info["group_name"]
                    if group not in groups_packages:
                        groups_packages[group] = []
                    pkg_name = pkg_info["package_name"]
                    if pkg_info["type"] == "image" and pkg_info.get("version"):
                        pkg_name = f"{pkg_name}:{pkg_info['version']}"
                    mirror_entry = existing_packages.get(_hash, {})
                    groups_packages[group].append({
                        "name": pkg_name,
                        "type": pkg_info["type"],
                        "repo_name": mirror_entry.get("source", ""),
                        "status": "Success" if mirror_entry.get("status") == "mirrored" else "Failed",
                        "catalog_name": catalog_name,
                    })

            if not groups_packages:
                continue

            # Sanitize catalog name for directory
            catalog_dir_name = f"catalog_{catalog_name.replace(' ', '_').replace('-', '_').lower()}"
            csv_base = os.path.join(status_base_dir, catalog_dir_name, arch)

            # Write group_status.csv
            group_entries = []
            for group_name, pkgs in groups_packages.items():
                all_success = all(p["status"] == "Success" for p in pkgs)
                group_entries.append({
                    "name": group_name,
                    "status": "success" if all_success else "failed"
                })
            write_group_status_csv(
                os.path.join(csv_base, "group_status.csv"),
                group_entries, logger)

            # Write per-group package_status.csv
            for group_name, pkgs in groups_packages.items():
                write_package_status_csv(
                    os.path.join(csv_base, group_name, "package_status.csv"),
                    pkgs, logger)

    logger.info("Generated multi-catalog status files in %s", status_base_dir)
