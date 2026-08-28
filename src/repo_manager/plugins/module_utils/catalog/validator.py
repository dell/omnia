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
# pylint: disable=too-many-branches,too-many-locals
"""
Catalog validation: JSON schema validation and business rule checks.
"""

import json
import logging

logger = logging.getLogger(__name__)

VALID_PACKAGE_TYPES = {'rpm', 'tarball', 'image', 'rpm_repo'}


def _validate_schema(catalog, schema):
    """
    Validate catalog against JSON schema.

    Returns:
        list: List of issue dicts {'severity': 'error', 'message': ...}
    """
    issues = []
    try:
        import jsonschema
        jsonschema.validate(instance=catalog, schema=schema)
    except ImportError:
        logger.warning("jsonschema not installed, skipping schema validation")
        issues.append({
            'severity': 'warning',
            'message': 'jsonschema library not installed, schema validation skipped'
        })
    except jsonschema.ValidationError as e:
        issues.append({
            'severity': 'error',
            'message': f"Schema validation failed: {e.message}"
        })
    except jsonschema.SchemaError as e:
        issues.append({
            'severity': 'error',
            'message': f"Invalid schema: {e.message}"
        })
    return issues


def _validate_referential_integrity(catalog):
    """
    Check referential integrity between layers, groups, and packages.

    Returns:
        list: List of issue dicts.
    """
    issues = []
    cat = catalog.get('catalog', {})
    functional_layers = cat.get('functionallayer', [])
    groups = cat.get('groups', {})
    packages = cat.get('packages', {})

    # Check functional layer references
    for layer in functional_layers:
        layer_name = layer.get('name', '<unnamed>')
        for ref in layer.get('components', []):
            if ref not in groups:
                issues.append({
                    'severity': 'error',
                    'message': f"FunctionalLayer '{layer_name}' references missing group '{ref}'"
                })

    # Check group references
    for group_key, group in groups.items():
        for ref in group.get('components', []):
            if ref not in packages:
                issues.append({
                    'severity': 'error',
                    'message': f"Group '{group_key}' references missing package '{ref}'"
                })

    return issues


def _validate_business_rules(catalog):
    """
    Check business rules for functional layers, packages, and groups.

    Returns:
        list: List of issue dicts.
    """
    issues = []
    cat = catalog.get('catalog', {})
    functional_layers = cat.get('functionallayer', [])
    groups = cat.get('groups', {})
    packages = cat.get('packages', {})
    
    # Check functional layers are not empty
    if not functional_layers:
        issues.append({
            'severity': 'error',
            'message': 'Catalog must have at least one functional layer'
        })
    
    # Check each functional layer
    for layer in functional_layers:
        layer_name = layer.get('name', '<unnamed>')
        components = layer.get('components', [])
        
        # Check components are not empty
        if not components:
            issues.append({
                'severity': 'error',
                'message': f"Functional layer '{layer_name}' has no components"
            })
        
        # Check for exactly one base_os group in components
        base_os_count = 0
        for comp_ref in components:
            comp_group = groups.get(comp_ref, {})
            if comp_group.get('type') == 'base_os':
                base_os_count += 1
        
        if base_os_count == 0:
            issues.append({
                'severity': 'error',
                'message': f"Functional layer '{layer_name}' must have exactly one base_os group (found 0)"
            })
        elif base_os_count > 1:
            issues.append({
                'severity': 'error',
                'message': f"Functional layer '{layer_name}' must have exactly one base_os group (found {base_os_count})"
            })

    # Check for duplicate entries in group components
    for group_key, group in groups.items():
        components = group.get('components', [])
        seen = set()
        for comp in components:
            if comp in seen:
                issues.append({
                    'severity': 'error',
                    'message': f"Group '{group_key}' has duplicate component '{comp}'"
                })
            seen.add(comp)

    # Check base_os groups have os and os_version
    for group_key, group in groups.items():
        if group.get('type') == 'base_os':
            if not group.get('os'):
                issues.append({
                    'severity': 'error',
                    'message': f"base_os group '{group_key}' missing 'os' field"
                })
            if not group.get('os_version'):
                issues.append({
                    'severity': 'error',
                    'message': f"base_os group '{group_key}' missing 'os_version' field"
                })

    # Check packages
    for pkg_key, pkg in packages.items():
        pkg_type = pkg.get('packagetype', '')
        sources = pkg.get('sources', [])

        # Every package must have at least one source
        if not sources:
            issues.append({
                'severity': 'error',
                'message': f"Package '{pkg_key}' has no sources"
            })

        # Package type must be valid
        if pkg_type not in VALID_PACKAGE_TYPES:
            issues.append({
                'severity': 'error',
                'message': f"Package '{pkg_key}' has invalid packagetype '{pkg_type}'"
            })

        # Type-specific checks
        if pkg_type in ('rpm', 'rpm_repo'):
            for src in sources:
                if not src.get('reponame'):
                    issues.append({
                        'severity': 'error',
                        'message': f"Package '{pkg_key}' ({pkg_type}) source missing 'reponame'"
                    })

        if pkg_type == 'tarball':
            for src in sources:
                if not src.get('url'):
                    issues.append({
                        'severity': 'error',
                        'message': f"Package '{pkg_key}' (tarball) source missing 'url'"
                    })

        if pkg_type == 'image':
            if not pkg.get('tag'):
                issues.append({
                    'severity': 'error',
                    'message': f"Package '{pkg_key}' (image) missing 'tag'"
                })
            for src in sources:
                if not src.get('registry'):
                    issues.append({
                        'severity': 'error',
                        'message': f"Package '{pkg_key}' (image) source missing 'registry'"
                    })

    # Check for orphan packages (in packages{} but unreferenced by any group)
    all_referenced = set()
    for group in groups.values():
        all_referenced.update(group.get('components', []))
    for pkg_key in packages:
        if pkg_key not in all_referenced:
            issues.append({
                'severity': 'warning',
                'message': f"Orphan package '{pkg_key}' not referenced by any group"
            })

    # Check for orphan groups (in groups{} but unreferenced by any functional layer)
    fl_referenced = set()
    for layer in functional_layers:
        fl_referenced.update(layer.get('components', []))
    for group_key in groups:
        if group_key not in fl_referenced:
            issues.append({
                'severity': 'warning',
                'message': f"Orphan group '{group_key}' not referenced by any functional layer"
            })

    return issues


def validate_catalog(catalog, schema_path=None):
    """
    Validate a catalog with all validation layers.

    Args:
        catalog: Catalog dict (with 'catalog' root key).
        schema_path: Optional path to JSON schema file.

    Returns:
        list: List of issue dicts {'severity': 'error'|'warning', 'message': ...}
    """
    issues = []

    # Layer 1: Schema validation
    if schema_path:
        try:
            with open(schema_path, 'r', encoding='utf-8') as fh:
                schema = json.load(fh)
            issues.extend(_validate_schema(catalog, schema))
        except FileNotFoundError:
            issues.append({
                'severity': 'warning',
                'message': f"Schema file not found: {schema_path}"
            })
        except json.JSONDecodeError as e:
            issues.append({
                'severity': 'error',
                'message': f"Invalid schema JSON: {e}"
            })

    # Layer 2: Referential integrity
    issues.extend(_validate_referential_integrity(catalog))

    # Layer 3: Business rules
    issues.extend(_validate_business_rules(catalog))

    return issues


def format_issues(issues):
    """Format issues for display."""
    lines = []
    errors = [i for i in issues if i['severity'] == 'error']
    warnings = [i for i in issues if i['severity'] == 'warning']

    for issue in errors:
        lines.append(f"[ERROR] {issue['message']}")
    for issue in warnings:
        lines.append(f"[WARNING] {issue['message']}")

    lines.append(f"\nSummary: {len(errors)} error(s), {len(warnings)} warning(s)")
    return '\n'.join(lines)
