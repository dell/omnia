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

logger = logging.getLogger(__name__)


def slugify(text):
    """Convert text to a valid identifier (lowercase, underscores)."""
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug or 'catalog'


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


def write_catalog(catalog, filepath):
    """
    Write a catalog to a JSON file.

    Args:
        catalog: Catalog data dict (must have 'catalog' root key).
        filepath: Path to write the catalog JSON file.

    Raises:
        OSError: If the file cannot be written.
    """
    # Ensure parent directory exists
    parent_dir = os.path.dirname(filepath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    logger.info("Writing catalog to: %s", filepath)
    with open(filepath, 'w', encoding='utf-8') as fh:
        json.dump(catalog, fh, indent=2)


def new_catalog(name, groups, packages, description='', version='1.0'):
    """
    Create a new catalog structure.

    Args:
        name: Catalog name.
        groups: Dict of group_key -> group_entry.
        packages: Dict of pkg_key -> package_entry.
        description: Optional catalog description.
        version: Catalog version string.

    Returns:
        dict: Complete catalog structure.
    """
    return {
        "catalog": {
            "name": name,
            "version": version,
            "identifier": slugify(name),
            "description": description,
            "functionallayer": [],
            "groups": groups,
            "packages": packages
        }
    }


def catalog_exists(filepath):
    """Check if a catalog file exists."""
    return os.path.isfile(filepath)
