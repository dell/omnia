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
Catalog Manager CLI - Entry point for catalog operations.

Usage:
    catalog_manager.py generate --input <file> --output <file> [options]
    catalog_manager.py add --input <file> --catalog <file> [--output <file>] [options]
    catalog_manager.py delete --input <file> --catalog <file> [--output <file>]
    catalog_manager.py validate --catalog <file> [--schema <file>]
"""

import argparse
import json
import logging
import os
import sys

# Add parent directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pylint: disable=wrong-import-position
from catalog.parser import parse_input_file, parse_delete_file
from catalog.catalog_io import (
    read_catalog, write_catalog, new_catalog as create_new_catalog, catalog_exists
)
from catalog.mutator import upsert_packages, delete_packages
from catalog.validator import validate_catalog, format_issues
from catalog.transformer import detect_schema_version, transform, write_keymap
from catalog.optimizer import optimize


def setup_logging(log_dir=None, log_file='catalog_manager.log'):
    """Setup logging configuration."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(console)

    # File handler if log_dir provided
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, log_file)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        ))
        logger.addHandler(file_handler)
        logging.info("Log file: %s", log_path)

    return logger


def cmd_generate(args):
    """Generate a new catalog from input file."""
    logger = logging.getLogger(__name__)

    if catalog_exists(args.output) and not args.force:
        logger.error("Output file '%s' already exists. Use --force to overwrite.", args.output)
        return 1

    try:
        parsed = parse_input_file(
            args.input,
            default_arch=args.default_arch,
            default_os=args.default_os,
            default_os_version=args.default_os_version
        )
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to parse input file: %s", e)
        return 1

    catalog = create_new_catalog(
        args.name,
        parsed['groups'],
        parsed['packages'],
        functional_layers=parsed.get('functional_layers', [])
    )
    write_catalog(catalog, args.output)

    # Optional validation
    if args.validate and args.schema:
        issues = validate_catalog(catalog, args.schema)
        if issues:
            print(format_issues(issues))
            errors = [i for i in issues if i['severity'] == 'error']
            if errors:
                logger.warning("Catalog generated with validation errors")

    fl_count = len(parsed.get('functional_layers', []))
    group_count = len(parsed['groups'])
    pkg_count = len(parsed['packages'])
    print(f"Catalog generated: {fl_count} functional layers, {group_count} groups, "
          f"{pkg_count} packages -> {args.output}")
    return 0


def cmd_add(args):
    """Add packages to existing catalog."""
    logger = logging.getLogger(__name__)

    try:
        catalog = read_catalog(args.catalog)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to read catalog: %s", e)
        return 1

    try:
        parsed = parse_input_file(
            args.input,
            default_arch=args.default_arch,
            default_os=args.default_os,
            default_os_version=args.default_os_version
        )
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to parse input file: %s", e)
        return 1

    summary = upsert_packages(catalog, parsed)
    output_file = args.output or args.catalog
    write_catalog(catalog, output_file)

    # Optional validation
    if args.validate and args.schema:
        issues = validate_catalog(catalog, args.schema)
        if issues:
            print(format_issues(issues))

    print(f"Added: {summary['added']}, Updated: {summary['updated']}, "
          f"Groups created: {summary['groups_created']} -> {output_file}")
    return 0


def cmd_delete(args):
    """Delete packages from catalog."""
    logger = logging.getLogger(__name__)

    try:
        catalog = read_catalog(args.catalog)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to read catalog: %s", e)
        return 1

    try:
        parsed_delete = parse_delete_file(args.input)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to parse delete file: %s", e)
        return 1

    summary = delete_packages(catalog, parsed_delete)
    output_file = args.output or args.catalog
    write_catalog(catalog, output_file)

    # Optional validation
    if args.validate and args.schema:
        issues = validate_catalog(catalog, args.schema)
        if issues:
            print(format_issues(issues))

    print(f"Deleted: {summary['deleted']}, Groups removed: {summary['groups_removed']}, "
          f"Skipped: {summary['skipped']} -> {output_file}")
    return 0


def cmd_validate(args):
    """Validate a catalog."""
    logger = logging.getLogger(__name__)

    try:
        catalog = read_catalog(args.catalog)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to read catalog: %s", e)
        return 1

    issues = validate_catalog(catalog, args.schema)
    print(format_issues(issues))

    errors = [i for i in issues if i['severity'] == 'error']
    return 1 if errors else 0


def cmd_transform(args):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Transform catalog from 1.0 to 2.0 format."""
    logger = logging.getLogger(__name__)

    # Check if output file exists
    output_file = args.output
    if catalog_exists(output_file) and not args.force:
        logger.error("Output file '%s' already exists. Use --force to overwrite.",
                     output_file)
        return 1

    # Read input file
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("Input file '%s' not found", args.input)
        return 1
    except json.JSONDecodeError as e:
        logger.error("Failed to parse input JSON: %s", e)
        return 1

    # Detect schema version
    try:
        version = detect_schema_version(data)
    except ValueError as e:
        logger.error(str(e))
        return 1

    if version == '2.0':
        logger.warning("Input catalog is already Schema 2.0 - no transformation needed")
        return 0

    # Transform
    print("═══ Catalog Transform: 1.0 → 2.0 ═══")
    print(f"Input:   {args.input}  (Schema {version} detected)")
    print(f"Output:  {output_file}")

    old_catalog = data['Catalog']
    catalog_data, key_map, warnings = transform(old_catalog)

    # Write output
    write_catalog(catalog_data, output_file)

    # Write keymap
    keymap_path = output_file + ".keymap.json"
    total_groups = len(catalog_data['catalog']['groups'])
    total_layers = len(catalog_data['catalog']['functionallayer'])
    write_keymap(key_map, args.input, output_file, keymap_path,
                 total_groups, total_layers)
    print(f"Keymap:  {keymap_path}")

    # Print package transformation report
    print("\n── Package Transformation ──")
    total_packages = len(catalog_data['catalog']['packages'])
    print(f"  Total packages: {total_packages}")

    # Count by type
    type_counters = {}
    for pkg in catalog_data['catalog']['packages'].values():
        ptype = pkg['packagetype']
        type_counters[ptype] = type_counters.get(ptype, 0) + 1

    for ptype in sorted(type_counters.keys()):
        print(f"  {ptype:12s}: {type_counters[ptype]}")

    # Print group creation report
    print("\n── Group Creation ──")
    baseos_groups = [k for k, v in catalog_data['catalog']['groups'].items()
                     if v['type'] == 'base_os']
    other_groups = [k for k, v in catalog_data['catalog']['groups'].items()
                    if v['type'] != 'base_os']
    print(f"  BaseOS groups:          {len(baseos_groups)} "
          f"({', '.join(baseos_groups)})")
    print(f"  FunctionalLayer groups: {len(other_groups)}")

    # Print functional layer rewiring
    print("\n── FunctionalLayer Rewiring ──")
    print(f"  Layers rewired: {total_layers}")
    if baseos_groups:
        print(f"  Each layer includes: {', '.join(baseos_groups)} + "
              "layer-specific group")

    # Print warnings
    print("\n── Warnings ──")
    if warnings:
        print(f"  {len(warnings)} warning(s)")
        for w in warnings[:10]:  # Limit to first 10
            print(f"  - {w}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more (see log)")
    else:
        print("  No warnings")

    # Auto-validate if schema provided
    print("\n── Post-Transform Validation ──")
    if args.schema:
        issues = validate_catalog(catalog_data, args.schema)
        errors = [i for i in issues if i['severity'] == 'error']
        if errors:
            print(f"  ⚠ Validation found {len(errors)} error(s) - review recommended")
            for issue in errors[:5]:
                print(f"    - {issue['message']}")
            if len(errors) > 5:
                print(f"    ... and {len(errors) - 5} more")
        else:
            print("  ✔ Validation passed")
    else:
        print("  (skipped - no schema provided)")

    print("\n✔ Transform complete")
    return 0


def cmd_optimize(args):  # pylint: disable=too-many-statements
    """Optimize catalog by extracting common packages."""
    logger = logging.getLogger(__name__)

    # Read catalog
    try:
        catalog = read_catalog(args.catalog)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to read catalog: %s", e)
        return 1

    # Verify 2.0 format
    try:
        version = detect_schema_version(catalog)
        if version != '2.0':
            logger.error("Optimize requires a Schema 2.0 catalog (found %s)", version)
            return 1
    except ValueError as e:
        logger.error(str(e))
        return 1

    print("═══ Catalog Optimize ═══")
    print(f"Input:   {args.catalog}")
    print(f"Output:  {args.output}")
    print(f"Threshold: {args.threshold} common packages\n")

    # Optimize
    optimized_catalog, summary = optimize(catalog, args.threshold)

    # Check if any changes were made
    if summary.get('message') and 'nothing to optimize' in summary['message'].lower():
        print(summary['message'])
        # Write unchanged catalog to output
        if args.output != args.catalog:
            write_catalog(catalog, args.output)
        return 0

    msg = summary.get('message', '')
    if msg and ('already exists' in msg or 'already covers' in msg):
        print(summary['message'])
        # Write unchanged catalog to output
        if args.output != args.catalog:
            write_catalog(catalog, args.output)
        return 0

    # Write optimized catalog
    write_catalog(optimized_catalog, args.output)

    # Print detailed report
    print("── Optimization Summary ──")
    print(f"  Iterations: {summary['iterations']}")
    print(f"  Shared groups created: {len(summary['shared_groups_created'])}")
    for sg in summary['shared_groups_created']:
        print(f"    - {sg}")

    print("\n── Common Packages ──")
    print(f"  Total unique common packages extracted: "
          f"{summary['total_common_packages']}")

    print("\n── Group Refactoring ──")
    print(f"  Groups refactored: {summary['groups_refactored']}")
    if summary['groups_removed']:
        removed_groups = ', '.join(summary['groups_removed'])
        print(f"  Groups removed (empty): {len(summary['groups_removed'])} "
              f"({removed_groups})")

    print("\n── Duplication Reduction ──")
    print(f"  Component references before: {summary['before_refs']}")
    print(f"  Component references after:  {summary['after_refs']}")
    print(f"  Reduction: {summary['reduction_pct']}%")

    print("\n✔ Optimization complete")
    return 0


def main():
    """Main entry point."""
    # Get CATALOG_FILE_PATH environment variable as default
    catalog_file_path = os.environ.get('CATALOG_FILE_PATH', '')
    
    parser = argparse.ArgumentParser(
        description='Catalog Manager - Generate, modify, and validate service catalogs',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--log-dir', help='Directory for log files')

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Generate command
    gen_parser = subparsers.add_parser('generate',
                                       help='Generate new catalog from input file')
    gen_parser.add_argument('--input', '-i', help='Input file path')
    gen_parser.add_argument('--output', '-o', default=catalog_file_path,
                            help=f'Output catalog file path '
                                 f'(default: $CATALOG_FILE_PATH={catalog_file_path})')
    gen_parser.add_argument('--name', '-n', default='default', help='Catalog name')
    gen_parser.add_argument('--force', '-f', action='store_true',
                            help='Overwrite existing file')
    gen_parser.add_argument('--default-arch', default='x86_64',
                            help='Default architecture')
    gen_parser.add_argument('--default-os', default='rhel', help='Default OS')
    gen_parser.add_argument('--default-os-version', default='10.0',
                            help='Default OS version')
    gen_parser.add_argument('--schema', help='Schema file for validation')
    gen_parser.add_argument('--validate', action='store_true', default=True,
                            help='Validate after generation')
    gen_parser.set_defaults(func=cmd_generate)

    # Add command
    add_parser = subparsers.add_parser('add',
                                       help='Add packages to existing catalog')
    add_parser.add_argument('--input', '-i', help='Input file with packages to add')
    add_parser.add_argument('--catalog', '-c', default=catalog_file_path,
                            help=f'Existing catalog file '
                                 f'(default: $CATALOG_FILE_PATH={catalog_file_path})')
    add_parser.add_argument('--output', '-o',
                            help='Output file (default: overwrite catalog)')
    add_parser.add_argument('--default-arch', default='x86_64',
                            help='Default architecture')
    add_parser.add_argument('--default-os', default='rhel', help='Default OS')
    add_parser.add_argument('--default-os-version', default='10.0',
                            help='Default OS version')
    add_parser.add_argument('--schema', help='Schema file for validation')
    add_parser.add_argument('--validate', action='store_true', default=True,
                            help='Validate after add')
    add_parser.set_defaults(func=cmd_add)

    # Delete command
    del_parser = subparsers.add_parser('delete',
                                       help='Delete packages from catalog')
    del_parser.add_argument('--input', '-i',
                            help='Input file with packages to delete')
    del_parser.add_argument('--catalog', '-c', default=catalog_file_path,
                            help=f'Existing catalog file '
                                 f'(default: $CATALOG_FILE_PATH={catalog_file_path})')
    del_parser.add_argument('--output', '-o',
                            help='Output file (default: overwrite catalog)')
    del_parser.add_argument('--schema', help='Schema file for validation')
    del_parser.add_argument('--validate', action='store_true', default=True,
                            help='Validate after delete')
    del_parser.set_defaults(func=cmd_delete)

    # Validate command
    val_parser = subparsers.add_parser('validate', help='Validate a catalog')
    val_parser.add_argument('--catalog', '-c', default=catalog_file_path,
                            help=f'Catalog file to validate '
                                 f'(default: $CATALOG_FILE_PATH={catalog_file_path})')
    val_parser.add_argument('--schema', '-s', help='JSON schema file')
    val_parser.set_defaults(func=cmd_validate)

    # Transform command
    trans_parser = subparsers.add_parser('transform',
                                         help='Transform catalog from 1.0 to 2.0 format')
    trans_parser.add_argument('--input', '-i', required=True,
                              help='Input 1.0 catalog file')
    trans_parser.add_argument('--output', '-o', required=True,
                              help='Output 2.0 catalog file')
    trans_parser.add_argument('--schema', '-s',
                              help='Schema file for post-transform validation')
    trans_parser.add_argument('--force', '-f', action='store_true',
                              help='Overwrite existing output file')
    trans_parser.set_defaults(func=cmd_transform)

    # Optimize command
    opt_parser = subparsers.add_parser('optimize',
                                       help='Optimize catalog by extracting common packages')
    opt_parser.add_argument('--catalog', '-c', required=True,
                            help='Input 2.0 catalog file')
    opt_parser.add_argument('--output', '-o', required=True,
                            help='Output optimized catalog file')
    opt_parser.add_argument('--threshold', '-t', type=int, default=10,
                            help='Minimum number of common packages to extract '
                                 '(default: 10)')
    opt_parser.set_defaults(func=cmd_optimize)

    args = parser.parse_args()

    # Validate required arguments
    if args.command == 'generate':
        if not args.input:
            parser.error("generate: --input is required")
        if not args.output:
            parser.error("generate: --output is required "
                         "(set CATALOG_FILE_PATH or use -o)")
    elif args.command in ('add', 'delete'):
        if not args.input:
            parser.error(f"{args.command}: --input is required")
        if not args.catalog:
            parser.error(f"{args.command}: --catalog is required "
                         "(set CATALOG_FILE_PATH or use -c)")
    elif args.command == 'validate':
        if not args.catalog:
            parser.error("validate: --catalog is required "
                         "(set CATALOG_FILE_PATH or use -c)")

    setup_logging(args.log_dir)

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
