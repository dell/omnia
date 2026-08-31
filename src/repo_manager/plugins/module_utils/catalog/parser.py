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
# pylint: disable=too-many-branches,too-many-locals,too-many-statements
"""
Input file parser for catalog operations.

Parses the INI-like input format:
  [defaults]
  arch=x86_64, os=rhel, os_version=10.0

  [group_key | type=base_os, description=..., os=rhel, os_version=10.0]
  pkg_key, rpm, name, reponame
  pkg_key, tarball, name, url
  pkg_key, image, image_path, registry, tag
"""

import re
import logging

logger = logging.getLogger(__name__)

# Regex patterns
DEFAULTS_HEADER = re.compile(r'^\[defaults\]\s*$', re.IGNORECASE)
GROUP_HEADER = re.compile(r'^\[([^\]|]+)(?:\s*\|\s*([^\]]*))?\]\s*$')
KV_PAIR = re.compile(r'(\w+)\s*=\s*([^,\]]+)')


def _parse_kv_pairs(text):
    """Parse key=value pairs from a string."""
    return {m.group(1).lower().strip(): m.group(2).strip() for m in KV_PAIR.finditer(text)}


def _parse_trailing_overrides(fields, start_index):
    """Parse trailing key=value overrides from positional fields."""
    overrides = {}
    for field in fields[start_index:]:
        if '=' in field:
            kv = _parse_kv_pairs(field)
            overrides.update(kv)
    return overrides


def _build_package_entry(pkg_type, fields, defaults, overrides):
    """Build a package entry dict based on package type."""
    arch = overrides.get('arch', defaults['arch'])
    os_name = overrides.get('os', defaults['os'])
    os_version = overrides.get('os_version', defaults['os_version'])

    if pkg_type in ('rpm', 'rpm_repo'):
        # fields: [pkg_key, type, name, reponame, ...]
        name = fields[2] if len(fields) > 2 else fields[0]
        reponame = fields[3] if len(fields) > 3 else ''
        return {
            "name": name,
            "packagetype": pkg_type,
            "sources": [{
                "architecture": arch,
                "reponame": reponame,
                "name": os_name,
                "version": [os_version]
            }]
        }
    elif pkg_type == 'tarball':
        # fields: [pkg_key, tarball, name, url, ...]
        name = fields[2] if len(fields) > 2 else fields[0]
        url = fields[3] if len(fields) > 3 else ''
        return {
            "name": name,
            "packagetype": "tarball",
            "sources": [{
                "architecture": arch,
                "name": os_name,
                "version": [os_version],
                "url": url
            }]
        }
    elif pkg_type == 'image':
        # fields: [pkg_key, image, image_path, registry, tag, ...]
        image_path = fields[2] if len(fields) > 2 else fields[0]
        registry = fields[3] if len(fields) > 3 else ''
        tag = fields[4] if len(fields) > 4 else 'latest'
        return {
            "name": image_path,
            "packagetype": "image",
            "tag": tag,
            "sources": [{
                "architecture": arch,
                "registry": registry
            }]
        }
    else:
        raise ValueError(f"Unknown package type: {pkg_type}")


def parse_input_file(filepath, default_arch='x86_64', default_os='rhel', default_os_version='10.0'):
    """
    Parse an input file for catalog generate/add operations.

    Args:
        filepath: Path to the input file.
        default_arch: Default architecture if not specified.
        default_os: Default OS if not specified.
        default_os_version: Default OS version if not specified.

    Returns:
        dict: {'functional_layers': [...], 'groups': {...}, 'packages': {...}}

    Raises:
        ValueError: On parse errors (duplicate groups, package before group, etc.)
        FileNotFoundError: If input file doesn't exist.
    """
    defaults = {
        'arch': default_arch,
        'os': default_os,
        'os_version': default_os_version
    }
    functional_layers = []
    groups = {}
    packages = {}
    current_section = None
    current_section_type = None
    line_num = 0

    with open(filepath, 'r', encoding='utf-8') as fh:
        for line in fh:
            line_num += 1
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Check for [defaults] header
            if DEFAULTS_HEADER.match(line):
                current_section = '__defaults__'
                current_section_type = 'defaults'
                continue

            # Check for section header (group or functional layer)
            section_match = GROUP_HEADER.match(line)
            if section_match:
                section_key = section_match.group(1).strip()
                metadata_str = section_match.group(2) or ''

                # Parse section metadata
                meta = _parse_kv_pairs(metadata_str)
                section_type = meta.get('type', 'group')
                section_desc = meta.get('description', '')

                if section_type == 'functional_layer':
                    # Functional layer: components are group references
                    fl_entry = {
                        "name": section_key,
                        "components": []
                    }
                    functional_layers.append(fl_entry)
                    current_section = fl_entry
                    current_section_type = 'functional_layer'
                else:
                    # Regular group or base_os group
                    if section_key in groups:
                        raise ValueError(f"Line {line_num}: Duplicate group '{section_key}'")

                    group_entry = {
                        "name": section_key,
                        "type": section_type,
                        "description": section_desc,
                        "components": []
                    }
                    if section_type == 'base_os':
                        group_entry['os'] = meta.get('os', defaults['os'])
                        group_entry['os_version'] = meta.get('os_version', defaults['os_version'])

                    groups[section_key] = group_entry
                    current_section = section_key
                    current_section_type = 'group'
                continue

            # If we're in the defaults section, parse key=value pairs
            if current_section_type == 'defaults':
                # Line like: arch=x86_64, os=rhel, os_version=10.0
                kv = _parse_kv_pairs(line)
                if 'arch' in kv:
                    defaults['arch'] = kv['arch']
                if 'os' in kv:
                    defaults['os'] = kv['os']
                if 'os_version' in kv:
                    defaults['os_version'] = kv['os_version']
                continue

            # Content line
            if current_section is None:
                raise ValueError(f"Line {line_num}: Content before any section header")

            # If we're in a functional layer, the line is a group reference
            if current_section_type == 'functional_layer':
                # Remove quotes and trailing comma if present
                group_ref = line.strip().strip(',').strip('"').strip("'")
                if group_ref:
                    current_section['components'].append(group_ref)
                continue

            # Otherwise, it's a package line in a group
            # Split by comma, strip each field
            fields = [f.strip() for f in line.split(',')]
            if len(fields) < 2:
                raise ValueError(f"Line {line_num}: Package line needs at least key and type")

            pkg_key = fields[0]
            pkg_type = fields[1].lower()

            if pkg_type not in ('rpm', 'rpm_repo', 'tarball', 'image'):
                raise ValueError(f"Line {line_num}: Unknown package type '{pkg_type}'")

            # Determine where trailing overrides start
            override_start = 4  # Default for rpm/rpm_repo/tarball
            if pkg_type == 'image':
                override_start = 5

            overrides = _parse_trailing_overrides(fields, override_start)
            pkg_entry = _build_package_entry(pkg_type, fields, defaults, overrides)
            packages[pkg_key] = pkg_entry
            groups[current_section]['components'].append(pkg_key)

    logger.info("Parsed input file: %d functional layers, %d groups, %d packages",
                len(functional_layers), len(groups), len(packages))
    return {'functional_layers': functional_layers, 'groups': groups, 'packages': packages}


def parse_delete_file(filepath):
    """
    Parse a delete input file (simplified format).

    Format:
        [group_key]
        pkg_key1
        pkg_key2

    Args:
        filepath: Path to the delete input file.

    Returns:
        dict: {group_key: [pkg_key, pkg_key, ...], ...}

    Raises:
        FileNotFoundError: If input file doesn't exist.
    """
    result = {}
    current_group = None
    line_num = 0

    with open(filepath, 'r', encoding='utf-8') as fh:
        for line in fh:
            line_num += 1
            line = line.strip()

            if not line or line.startswith('#'):
                continue

            # Group header: [group_key]
            group_match = GROUP_HEADER.match(line)
            if group_match:
                current_group = group_match.group(1).strip()
                if current_group not in result:
                    result[current_group] = []
                continue

            # Package key line
            if current_group is None:
                raise ValueError(f"Line {line_num}: Package key before any group header")

            # The line is just a package key
            pkg_key = line.split(',')[0].strip()  # Handle trailing commas gracefully
            if pkg_key:
                result[current_group].append(pkg_key)

    logger.info("Parsed delete file: %d groups", len(result))
    return result
