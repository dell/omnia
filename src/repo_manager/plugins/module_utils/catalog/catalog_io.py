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
Catalog I/O operations: read and write catalog JSON files.
"""

import os
import json
import re
import logging
import tempfile

logger = logging.getLogger(__name__)


class CatalogPathError(ValueError):
    """Raised when a catalog path resolves outside its allowed root."""


def resolve_and_validate_catalog_path(filepath, allowed_root):
    """Resolve `filepath` to an absolute, symlink-free path and confirm it
    falls inside `allowed_root`.

    This is the code-level enforcement of the catalog-editing/bulk-edit-
    catalog skills' Write-Path Boundary (NFR-2, Req-SEC-I-1/I-4): a resolved
    path outside the allowed root -- whether via an absolute path elsewhere
    on the filesystem, a relative path containing `..` that escapes it, or a
    symlink (in the path's directory or the leaf itself) that redirects into
    it -- is rejected before any write is attempted.

    Args:
        filepath: The path a caller wants to write to (need not exist yet).
        allowed_root: The catalog repository root writes must stay under.

    Returns:
        str: The resolved, symlink-free absolute path, guaranteed to be
        inside `allowed_root`.

    Raises:
        CatalogPathError: If the resolved path is not inside `allowed_root`.
    """
    allowed_root_real = os.path.realpath(allowed_root)
    candidate = os.path.abspath(filepath)

    # Resolve the parent directory chain (which may already contain a
    # symlink hop) independently of the leaf filename, since the leaf itself
    # may not exist yet -- os.path.realpath on a nonexistent path simply
    # normalizes it, which is what we want for the not-yet-written file, but
    # any symlink *earlier* in the path must still be followed and checked.
    parent_dir = os.path.dirname(candidate) or os.sep
    resolved_parent = os.path.realpath(parent_dir)
    resolved_path = os.path.join(resolved_parent, os.path.basename(candidate))

    # If the leaf itself is already a symlink (e.g. overwriting an existing
    # catalog file that was replaced by a symlink pointing elsewhere), follow
    # it too so that escape is caught rather than silently written through.
    if os.path.islink(resolved_path):
        resolved_path = os.path.realpath(resolved_path)

    try:
        is_contained = os.path.commonpath([resolved_path, allowed_root_real]) == allowed_root_real
    except ValueError:
        # commonpath raises when paths don't share a drive/root (e.g. mixed
        # UNC paths on Windows) -- that is never containment.
        is_contained = False

    if not is_contained:
        raise CatalogPathError(
            f"Refusing to write outside the catalog repository root: "
            f"'{filepath}' resolves to '{resolved_path}', which is not "
            f"under '{allowed_root_real}'."
        )
    return resolved_path


def slugify(text):
    """Convert text to a valid identifier (lowercase, underscores)."""
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug or 'catalog'


def find_path_collisions(labeled_paths):
    """Find every pair of distinct, falsy-filtered paths that resolve to the
    same real filesystem location.

    Comparing raw strings misses a symlink alias (e.g. an output path that is
    actually a symlink to one of the input catalogs) and misses two
    differently-spelled paths (`./x.json` vs `x.json`) that are really the
    same file. Resolving with `os.path.realpath()` first catches both, and
    works even for a path that does not exist yet (an output file that will
    be created) since `realpath()` only needs the path's existing ancestor
    directories to resolve symlinks -- the not-yet-existing leaf is just
    normalized.

    Args:
        labeled_paths: dict of {label: path}. Falsy paths (None/'') are
            ignored -- an unset optional output is not a collision candidate.

    Returns:
        list of (label_a, label_b, resolved_path) tuples, one per colliding
        pair, in the order the labels were first seen.
    """
    resolved = [
        (label, os.path.realpath(path))
        for label, path in labeled_paths.items() if path
    ]
    collisions = []
    for i, (label_a, path_a) in enumerate(resolved):
        for label_b, path_b in resolved[i + 1:]:
            if path_a == path_b:
                collisions.append((label_a, label_b, path_a))
    return collisions


def read_catalog(filepath):
    """
    Read a catalog from a JSON file.

    Args:
        filepath: Path to the catalog JSON file.

    Returns:
        dict: Catalog data with 'catalog' as the root key.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If the catalog structure is invalid.
    """
    logger.info("Reading catalog from: %s", filepath)
    with open(filepath, 'r', encoding='utf-8') as fh:
        data = json.load(fh)

    if 'catalog' not in data:
        raise ValueError(f"Invalid catalog file: missing 'catalog' key in {filepath}")

    return data


def write_catalog(catalog, filepath, allowed_root=None):
    """
    Write a catalog to a JSON file.

    Args:
        catalog: Catalog data dict (must have 'catalog' root key).
        filepath: Path to write the catalog JSON file.
        allowed_root: Optional catalog repository root. When given, the
            resolved destination path is validated with
            `resolve_and_validate_catalog_path()` before anything is
            written, and the write itself is an atomic temporary-file
            replacement within the validated directory (write to a sibling
            temp file, then `os.replace()` it into place) so a failure
            partway through never leaves a truncated/corrupt catalog file.
            When omitted (the default, for callers that manage their own
            path boundary or intentionally write outside a fixed catalog
            tree), behavior is unchanged from before this check existed.

    Raises:
        CatalogPathError: If `allowed_root` is given and the resolved path
            falls outside it.
        OSError: If the file cannot be written.
    """
    if allowed_root is not None:
        filepath = resolve_and_validate_catalog_path(filepath, allowed_root)

    # Ensure parent directory exists
    parent_dir = os.path.dirname(filepath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    logger.info("Writing catalog to: %s", filepath)

    if allowed_root is None:
        with open(filepath, 'w', encoding='utf-8') as fh:
            json.dump(catalog, fh, indent=2)
        return

    # Atomic replacement: write to a temp file in the same (validated)
    # directory, then rename it into place. `os.replace()` is atomic on the
    # same filesystem, so a reader never observes a partially-written file,
    # and a crash/interrupt mid-write leaves the original file untouched.
    fd, tmp_path = tempfile.mkstemp(
        dir=parent_dir or '.', prefix='.catalog-', suffix='.tmp'
    )
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            json.dump(catalog, fh, indent=2)
        os.replace(tmp_path, filepath)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def new_catalog(name, groups, packages, functional_layers=None, description='', version='1.0'):
    """
    Create a new catalog structure.

    Args:
        name: Catalog name.
        groups: Dict of group_key -> group_entry.
        packages: Dict of pkg_key -> package_entry.
        functional_layers: List of functional layer entries (optional).
        description: Optional catalog description.
        version: Catalog version string.

    Returns:
        dict: Complete catalog structure.
    """
    if functional_layers is None:
        functional_layers = []
    
    return {
        "catalog": {
            "name": name,
            "version": version,
            "identifier": slugify(name),
            "description": description,
            "functionallayer": functional_layers,
            "groups": groups,
            "packages": packages
        }
    }


def catalog_exists(filepath):
    """Check if a catalog file exists."""
    return os.path.isfile(filepath)
