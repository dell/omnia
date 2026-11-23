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
import re

logger = logging.getLogger(__name__)

VALID_PACKAGE_TYPES = {'rpm', 'tarball', 'image', 'rpm_repo', 'git', 'manifest', 'pip_module'}


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
        issues.append({
            'severity': 'error',
            'message': 'Schema validation requires the jsonschema library; '
                       'install it in the Python environment running this command and retry'
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
        
        # Check for exactly one baseos group in components
        baseos_count = 0
        for comp_ref in components:
            comp_group = groups.get(comp_ref, {})
            if comp_group.get('type') == 'baseos':
                baseos_count += 1
        
        if baseos_count == 0:
            issues.append({
                'severity': 'error',
                'message': f"Functional layer '{layer_name}' must have exactly one baseos group (found 0)"
            })
        elif baseos_count > 1:
            issues.append({
                'severity': 'error',
                'message': f"Functional layer '{layer_name}' must have exactly one baseos group (found {baseos_count})"
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

    # Check baseos groups have os and os_version
    for group_key, group in groups.items():
        if group.get('type') == 'baseos':
            if not group.get('os'):
                issues.append({
                    'severity': 'error',
                    'message': f"baseos group '{group_key}' missing 'os' field"
                })
            if not group.get('os_version'):
                issues.append({
                    'severity': 'error',
                    'message': f"baseos group '{group_key}' missing 'os_version' field"
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

        if pkg_type == 'git':
            for src in sources:
                if not src.get('url'):
                    issues.append({
                        'severity': 'error',
                        'message': f"Package '{pkg_key}' (git) source missing 'url'"
                    })

        if pkg_type == 'manifest':
            for src in sources:
                if not src.get('url'):
                    issues.append({
                        'severity': 'error',
                        'message': f"Package '{pkg_key}' (manifest) source missing 'url'"
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


PREDEFINED_CATALOG_PREFIXES = (
    'service_kube_',
    'slurm_',
    'login_node_',
    'login_compiler_node_',
    'os_',
)
SUPPORTED_FLEXIBLE_ARCHITECTURES = ('x86_64', 'aarch64')
SUPPORTED_FLEXIBLE_OS_TOKENS = {
    ('rhel', '10.0'),
    ('rhel', '10.2'),
    ('rhel', '10_0'),
    ('rhel', '10_2'),
}
FLEXIBLE_GROUP_PATTERN = re.compile(
    r"^fg_(?P<label>[a-zA-Z0-9_-]+)_(?P<os>[a-z]+)_"
    r"(?P<version>[0-9]+(?:_[0-9]+)*)_(?P<arch>[a-zA-Z0-9_]+)$"
)


def _validate_flexible_functional_groups(catalog):
    """
    Validate flexible functional group contracts and authoring review status.

    Checks:
    - Non-predefined groups must use the mandatory 'fg_' prefix (FR-1.1).
    - No more than 10 flexible groups per catalog (AC-001).
    - Every flexible group must match fg_<label>_<os>_<version>_<arch> (FR-1.1).
    - Architecture must be x86_64 or aarch64 (blocking error) (AC-001, AC-003).
    - Non-RHEL 10.0/10.2 OS or version produces a non-blocking warning (AC-003).
    - Generated catalogs require operator review approval (ER-BSM-001 gate) (FR-1.1).
    """
    issues = []
    cat = catalog.get('catalog', {})
    functional_layers = cat.get('functionallayer', [])

    fg_layers = []
    for layer in functional_layers:
        name = layer.get('name', '')
        if name.startswith('fg_'):
            fg_layers.append(layer)
        elif not any(name.startswith(pre) for pre in PREDEFINED_CATALOG_PREFIXES):
            issues.append({
                'severity': 'error',
                'message': (
                    f"Functional layer '{name}' is missing the mandatory 'fg_' prefix "
                    "for flexible functional groups"
                )
            })

    # AC-001: Maximum 10 flexible groups
    if len(fg_layers) > 10:
        issues.append({
            'severity': 'error',
            'message': (
                f"Catalog contains {len(fg_layers)} flexible functional groups; "
                "maximum allowed is 10"
            )
        })

    # FR-1.1, AC-001, AC-003: Suffix, architecture, and platform checks
    for layer in fg_layers:
        name = layer.get('name', '')
        match = FLEXIBLE_GROUP_PATTERN.match(name)
        if not match:
            issues.append({
                'severity': 'error',
                'message': (
                    f"Flexible group '{name}' lacks required platform suffix "
                    "'<os-name>_<os-version>_<architecture>'"
                )
            })
            continue

        arch = match.group('arch')
        os_name = match.group('os')
        version = match.group('version')

        if arch not in SUPPORTED_FLEXIBLE_ARCHITECTURES:
            issues.append({
                'severity': 'error',
                'message': (
                    f"Flexible group '{name}' declares unsupported architecture '{arch}'; "
                    f"supported architectures are: {', '.join(SUPPORTED_FLEXIBLE_ARCHITECTURES)}"
                )
            })

        norm_version = version.replace('_', '.')
        if ((os_name, version) not in SUPPORTED_FLEXIBLE_OS_TOKENS
                and (os_name, norm_version) not in SUPPORTED_FLEXIBLE_OS_TOKENS):
            issues.append({
                'severity': 'warning',
                'message': (
                    f"Flexible group '{name}' specifies OS '{os_name}' version '{norm_version}'; "
                    "only RHEL 10.0 and 10.2 are qualified"
                )
            })

    # FR-1.1: Operator review gate for generated catalogs
    is_generated = (
        cat.get('generated') is True
        or cat.get('authoring', {}).get('generated') is True
        or 'generation' in cat
        or 'operator_review' in cat
        or 'review' in cat
    )
    if is_generated:
        review = cat.get('operator_review') or cat.get('review')
        if (not isinstance(review, dict)
                or not review.get('approved')
                or str(review.get('status', '')).lower() != 'approved'):
            issues.append({
                'severity': 'error',
                'message': (
                    "Generated catalog lacks valid operator review approval "
                    "(ER-BSM-001 authoring gate); review evidence is required "
                    "before catalog is authoritative"
                )
            })

    return issues


def validate_catalog(catalog, schema_path=None):
    """
    Validate a catalog with all validation layers.

    Args:
        catalog: Catalog dict (with 'catalog' root key).
        schema_path: Optional path to JSON schema file. When supplied, failure
            to read the schema or load jsonschema is a validation error.

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
                'severity': 'error',
                'message': f"Schema file not found: {schema_path}"
            })
        except OSError:
            issues.append({
                'severity': 'error',
                'message': f"Schema file could not be read: {schema_path}"
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

    # Layer 4: Flexible functional group contracts & review gate
    issues.extend(_validate_flexible_functional_groups(catalog))

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
