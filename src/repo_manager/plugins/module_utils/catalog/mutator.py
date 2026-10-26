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

import copy
import logging

logger = logging.getLogger(__name__)


def _source_identity(source):
    """Return the source fields other than its OS-version list."""
    return {k: v for k, v in source.items() if k != 'version'}


def merge_package_entry(existing, incoming):
    """
    Merge an incoming package entry into an existing one without dropping the
    sources of other architectures or OS versions.

    Top-level fields (name, tag, version, ...) come from `incoming`. Each
    incoming source takes over its (architecture, OS) pair for the OS versions
    it lists; the existing sources keep every other architecture and OS
    version. A source with no OS-version list (images) replaces the existing
    source of the same architecture. If the package type changes, the source
    shapes are incompatible and `incoming` replaces the entry outright.

    Args:
        existing: Package entry currently in the catalog.
        incoming: Package entry parsed from the input file.

    Returns:
        dict: The merged package entry (a new dict; inputs are not modified).
    """
    if existing.get('packagetype') != incoming.get('packagetype'):
        return copy.deepcopy(incoming)

    merged = copy.deepcopy(existing)
    merged.update({k: copy.deepcopy(v) for k, v in incoming.items() if k != 'sources'})
    sources = merged.setdefault('sources', [])

    for new_src in incoming.get('sources', []):
        new_src = copy.deepcopy(new_src)
        arch = new_src.get('architecture')
        os_name = new_src.get('name')
        new_versions = new_src.get('version')

        kept = []
        target = None
        for src in sources:
            if src.get('architecture') != arch or os_name not in (None, src.get('name')):
                kept.append(src)
            elif new_versions is None:
                # No OS-version list (e.g. image lines): this source replaces
                # the matching one, keeping fields the input cannot express.
                new_src = dict(src, **new_src)
            elif src.get('version') is None:
                continue
            elif target is None and _source_identity(src) == _source_identity(new_src):
                # Same source: extend its OS versions in place.
                src['version'] = src['version'] + [
                    v for v in new_versions if v not in src['version']]
                target = src
                kept.append(src)
            else:
                remaining = [v for v in src['version'] if v not in new_versions]
                if remaining:
                    kept.append(dict(src, version=remaining))
        sources[:] = kept

        if target is None:
            sources.append(new_src)

    return merged


def upsert_packages(catalog, parsed):
    """
    Add or update packages in a catalog (upsert semantics). Updating an
    existing package merges its sources (see `merge_package_entry`).

    Args:
        catalog: Catalog dict (with 'catalog' root key).
        parsed: Parsed input dict with 'functional_layers', 'groups', and 'packages'.

    Returns:
        dict: Summary with counts {'added', 'updated', 'groups_created', 'fl_created'}.
    """
    cat = catalog['catalog']
    functional_layers = cat.setdefault('functionallayer', [])
    groups = cat.setdefault('groups', {})
    packages = cat.setdefault('packages', {})

    summary = {'added': 0, 'updated': 0, 'groups_created': 0, 'fl_created': 0}

    # Process functional layers
    input_fl = parsed.get('functional_layers', [])
    existing_fl_names = {fl['name'] for fl in functional_layers}
    for fl_entry in input_fl:
        fl_name = fl_entry.get('name')
        if fl_name not in existing_fl_names:
            # Add new functional layer
            functional_layers.append(fl_entry)
            summary['fl_created'] += 1
            logger.info("Created new functional layer: %s", fl_name)
        else:
            # Merge components into existing functional layer
            for existing_fl in functional_layers:
                if existing_fl['name'] == fl_name:
                    existing_comps = set(existing_fl.get('components', []))
                    for comp in fl_entry.get('components', []):
                        if comp not in existing_comps:
                            existing_fl['components'].append(comp)
                            logger.debug("Added %s to functional layer %s", comp, fl_name)
                    break

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
            if group_entry.get('type') == 'baseos':
                groups[group_key]['os'] = group_entry.get('os', '')
                groups[group_key]['os_version'] = group_entry.get('os_version', '')
            summary['groups_created'] += 1
            logger.info("Created new group: %s", group_key)

    # Process packages
    for pkg_key, pkg_entry in parsed['packages'].items():
        if pkg_key in packages:
            # Update existing package, keeping other architectures/OS versions
            packages[pkg_key] = merge_package_entry(packages[pkg_key], pkg_entry)
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
            affected_layers = []
            for layer in functional_layers:
                if group_key in layer.get('components', []):
                    layer['components'].remove(group_key)
                    affected_layers.append(layer.get('name', ''))
            summary['groups_removed'] += 1
            logger.warning("Removed empty group [%s] from functional layer(s): %s",
                           group_key, ', '.join(affected_layers) or 'none')

    return summary
