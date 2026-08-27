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
Catalog mutation operations: add (upsert) and delete packages/groups.
"""

import logging

logger = logging.getLogger(__name__)


def upsert_packages(catalog, parsed):
    """
    Add or update packages in a catalog (upsert semantics).

    Args:
        catalog: Catalog dict (with 'catalog' root key).
        parsed: Parsed input dict with 'groups' and 'packages'.

    Returns:
        dict: Summary with counts {'added', 'updated', 'groups_created'}.
    """
    cat = catalog['catalog']
    groups = cat.setdefault('groups', {})
    packages = cat.setdefault('packages', {})

    summary = {'added': 0, 'updated': 0, 'groups_created': 0}

    # Process groups
    for group_key, group_entry in parsed['groups'].items():
        if group_key not in groups:
            # Create new group
            groups[group_key] = {
                'name': group_entry['name'],
                'type': group_entry.get('type', 'group'),
                'description': group_entry.get('description', ''),
                'components': []
            }
            if group_entry.get('type') == 'base_os':
                groups[group_key]['os'] = group_entry.get('os', '')
                groups[group_key]['os_version'] = group_entry.get('os_version', '')
            summary['groups_created'] += 1
            logger.info("Created new group: %s", group_key)

    # Process packages
    for pkg_key, pkg_entry in parsed['packages'].items():
        if pkg_key in packages:
            # Update existing package
            packages[pkg_key] = pkg_entry
            summary['updated'] += 1
            logger.info("Updated package: %s", pkg_key)
        else:
            # Add new package
            packages[pkg_key] = pkg_entry
            summary['added'] += 1
            logger.info("Added package: %s", pkg_key)

    # Ensure package keys are in their group's components list
    for group_key, group_entry in parsed['groups'].items():
        if group_key in groups:
            existing_components = set(groups[group_key].get('components', []))
            for pkg_key in group_entry.get('components', []):
                if pkg_key not in existing_components:
                    groups[group_key]['components'].append(pkg_key)
                    logger.debug("Added %s to group %s components", pkg_key, group_key)

    return summary


def delete_packages(catalog, parsed_delete):
    """
    Delete packages from a catalog.

    Args:
        catalog: Catalog dict (with 'catalog' root key).
        parsed_delete: Dict {group_key: [pkg_key, ...]}.

    Returns:
        dict: Summary with counts {'deleted', 'groups_removed', 'skipped'}.
    """
    cat = catalog['catalog']
    groups = cat.get('groups', {})
    packages = cat.get('packages', {})
    functional_layers = cat.get('functionallayer', [])

    summary = {'deleted': 0, 'groups_removed': 0, 'skipped': 0}

    for group_key, pkg_keys in parsed_delete.items():
        if group_key not in groups:
            logger.warning("Group [%s] not found - skipping", group_key)
            summary['skipped'] += len(pkg_keys)
            continue

        group = groups[group_key]
        components = group.get('components', [])

        for pkg_key in pkg_keys:
            if pkg_key not in components:
                logger.warning("Package '%s' not in group [%s] - skipping", pkg_key, group_key)
                summary['skipped'] += 1
                continue

            # Remove from group components
            components.remove(pkg_key)
            logger.info("Removed '%s' from group [%s]", pkg_key, group_key)

            # Check if package is still referenced by any group
            still_referenced = any(
                pkg_key in g.get('components', [])
                for g in groups.values()
            )

            if not still_referenced and pkg_key in packages:
                del packages[pkg_key]
                logger.info("Deleted package '%s' from catalog (no remaining references)", pkg_key)
            elif still_referenced:
                logger.info("Package '%s' retained (still referenced by other groups)", pkg_key)

            summary['deleted'] += 1

        # Remove empty groups
        if not components:
            del groups[group_key]
            # Also remove from functional layers
            for layer in functional_layers:
                if group_key in layer.get('components', []):
                    layer['components'].remove(group_key)
            summary['groups_removed'] += 1
            logger.info("Removed empty group [%s]", group_key)

    return summary
