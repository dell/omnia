#!/usr/bin/env python3
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
Catalog Optimizer - Extract common packages across functional layer groups.

This module provides functions to:
- Identify common packages across functional layer groups
- Create shared groups for common packages
- Refactor existing groups to remove duplicated packages
- Optimize catalog structure to reduce duplication
"""

from typing import Tuple
from itertools import combinations


def optimize(catalog: dict, threshold: int = 10) -> Tuple[dict, dict]:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """
    Extract common packages across functional layer groups into shared groups.

    This optimization iteratively:
    1. Identifies candidate groups (non-baseos groups in functional layers)
    2. Finds the largest subset of groups with intersection >= threshold
    3. Creates a shared group with common packages
    4. Removes common packages from original groups
    5. Rewires functional layers to include the shared group
    6. Repeats until no more common sets >= threshold exist

    Args:
        catalog: 2.0 format catalog dictionary
        threshold: Minimum number of common packages required (default: 10)

    Returns:
        Tuple of (modified_catalog, summary_dict)

    Summary dict contains:
        - iterations: Number of optimization iterations performed
        - shared_groups_created: List of shared group keys created
        - total_common_packages: Total unique common packages extracted
        - groups_refactored: Number of groups refactored
        - groups_removed: List of empty groups removed
        - before_refs: Total component references before
        - after_refs: Total component references after

    Raises:
        ValueError: If not a 2.0 catalog (missing lowercase 'catalog' key)
    """
    # Validate 2.0 catalog
    if 'catalog' not in catalog:
        raise ValueError("Not a 2.0 catalog - root key 'catalog' not found")

    cat = catalog['catalog']

    # Track overall statistics
    iterations = 0
    shared_groups_created = []
    all_refactored_groups = set()
    all_removed_groups = []
    count_before_refs = sum(len(g['components']) for g in cat['groups'].values()
                            if g['type'] != 'base_os')

    # Iteratively extract common packages
    while True:  # pylint: disable=too-many-nested-blocks
        # Step 1: Identify candidate groups
        layer_to_groups = {}  # layer_name -> [group_keys]
        group_to_layers = {}  # group_key -> [layer_names]

        for layer in cat.get('functionallayer', []):
            non_baseos_group_keys = []
            for group_key in layer['components']:
                if group_key in cat['groups']:
                    group = cat['groups'][group_key]
                    # Skip baseos and already-created shared groups
                    if (group['type'] != 'base_os' and
                            'common_shared_group' not in group_key):
                        non_baseos_group_keys.append(group_key)
                        if group_key not in group_to_layers:
                            group_to_layers[group_key] = []
                        group_to_layers[group_key].append(layer['name'])
            layer_to_groups[layer['name']] = non_baseos_group_keys

        # Collect all unique non-baseos, non-shared group keys
        candidate_group_keys = list(group_to_layers.keys())

        if len(candidate_group_keys) < 2:
            break  # No more groups to optimize

        # Step 2: Find the best subset with largest common intersection
        best_subset = None
        best_intersection = set()
        best_intersection_size = 0

        # Try all possible subsets of groups (starting from largest)
        for subset_size in range(len(candidate_group_keys), 1, -1):
            for subset in combinations(candidate_group_keys, subset_size):
                # Compute intersection
                group_sets = [set(cat['groups'][gk]['components']) for gk in subset]
                intersection = set.intersection(*group_sets)

                if (len(intersection) >= threshold and
                        len(intersection) > best_intersection_size):
                    best_intersection_size = len(intersection)
                    best_intersection = intersection
                    best_subset = subset

            # If we found a good subset, stop searching smaller subsets
            if best_subset:
                break

        # If no subset found with intersection >= threshold, we're done
        if not best_subset or best_intersection_size < threshold:
            break

        iterations += 1
        participating_group_keys = list(best_subset)
        common_packages = sorted(list(best_intersection))

        # Step 3: Create shared group
        shared_group_key = "common_shared_group"
        if iterations > 1:
            shared_group_key = f"common_shared_group_{iterations}"
        counter = 1
        while shared_group_key in cat['groups']:
            shared_group_key = f"common_shared_group_{iterations}_{counter}"
            counter += 1

        # Determine which layers participate
        participating_layer_names = []
        for gk in participating_group_keys:
            participating_layer_names.extend(group_to_layers[gk])
        participating_layer_names = sorted(set(participating_layer_names))

        layer_list = ', '.join(participating_layer_names)
        cat['groups'][shared_group_key] = {
            "name": shared_group_key,
            "type": "group",
            "description": (f"Auto-extracted: {len(common_packages)} common packages "
                            f"shared across {len(participating_layer_names)} functional "
                            f"layers ({layer_list})"),
            "components": common_packages
        }
        shared_groups_created.append(shared_group_key)

        # Step 4: Refactor participating groups
        groups_removed_this_iter = []

        for gk in participating_group_keys:
            old_components = cat['groups'][gk]['components']

            # Remove common packages from this group
            new_components = [c for c in old_components if c not in common_packages]

            if len(new_components) == 0:
                # Group is now empty - mark for removal
                groups_removed_this_iter.append(gk)
                all_removed_groups.append(gk)
                del cat['groups'][gk]
            else:
                cat['groups'][gk]['components'] = new_components
                desc = cat['groups'][gk].get('description', '')
                if 'layer-specific after optimization' not in desc:
                    suffix = " (layer-specific after optimization)"
                    cat['groups'][gk]['description'] = (desc + suffix if desc
                                                        else "Layer-specific after optimization")
                all_refactored_groups.add(gk)

        # Step 5: Rewire functional layers
        for layer in cat['functionallayer']:
            # Check if any of this layer's group references are in participating_group_keys
            layer_has_participating = False
            for comp in layer['components']:
                if comp in participating_group_keys:
                    layer_has_participating = True
                    break

            if layer_has_participating:
                # Insert shared_group_key after baseos groups, before layer-specific groups
                new_components = []
                shared_added = False

                for comp in layer['components']:
                    # Check if this is a baseos group
                    is_baseos = False
                    if comp in cat['groups'] and cat['groups'][comp]['type'] == 'base_os':
                        is_baseos = True

                    new_components.append(comp)

                    # After the last baseos group, insert the shared group
                    if is_baseos and not shared_added:
                        # Check if next component is also baseos
                        next_idx = layer['components'].index(comp) + 1
                        next_is_baseos = False
                        if next_idx < len(layer['components']):
                            next_comp = layer['components'][next_idx]
                            if (next_comp in cat['groups'] and
                                    cat['groups'][next_comp]['type'] == 'base_os'):
                                next_is_baseos = True

                        # Insert after last baseos
                        if not next_is_baseos:
                            new_components.append(shared_group_key)
                            shared_added = True

                # If no baseos was found, just prepend at position 0
                if not shared_added:
                    new_components.insert(0, shared_group_key)

                # Remove groups that were deleted (empty after extraction)
                new_components = [c for c in new_components
                                  if c not in groups_removed_this_iter]

                # Deduplicate while preserving order
                seen = set()
                deduplicated = []
                for item in new_components:
                    if item not in seen:
                        seen.add(item)
                        deduplicated.append(item)

                layer['components'] = deduplicated

    # If no iterations performed, nothing to optimize
    if iterations == 0:
        summary = {
            'iterations': 0,
            'shared_groups_created': [],
            'total_common_packages': 0,
            'groups_refactored': 0,
            'groups_removed': [],
            'before_refs': 0,
            'after_refs': 0,
            'message': (f'No common sets >= {threshold} found across layer groups - '
                        'nothing to optimize')
        }
        return catalog, summary

    # Build summary
    count_after_refs = sum(len(g['components']) for g in cat['groups'].values()
                           if g['type'] != 'base_os')

    reduction_pct = 0
    if count_before_refs > 0:
        reduction_pct = round(((count_before_refs - count_after_refs) /
                               count_before_refs) * 100, 1)

    # Count total unique common packages
    total_common_packages = set()
    for sg in shared_groups_created:
        if sg in cat['groups']:
            total_common_packages.update(cat['groups'][sg]['components'])

    summary = {
        'iterations': iterations,
        'shared_groups_created': shared_groups_created,
        'total_common_packages': len(total_common_packages),
        'groups_refactored': len(all_refactored_groups),
        'groups_removed': all_removed_groups,
        'before_refs': count_before_refs,
        'after_refs': count_after_refs,
        'reduction_pct': reduction_pct,
        'message': 'Optimization complete'
    }

    return catalog, summary
