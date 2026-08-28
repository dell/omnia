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
import logging
import os
import sys

# Add parent directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from catalog.parser import parse_input_file, parse_delete_file
from catalog.catalog_io import read_catalog, write_catalog, new_catalog, catalog_exists
from catalog.mutator import upsert_packages, delete_packages
from catalog.validator import validate_catalog, format_issues


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

    catalog = new_catalog(
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
    print(f"Catalog generated: {fl_count} functional layers, {group_count} groups, {pkg_count} packages -> {args.output}")
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
    gen_parser = subparsers.add_parser('generate', help='Generate new catalog from input file')
    gen_parser.add_argument('--input', '-i', help='Input file path')
    gen_parser.add_argument('--output', '-o', default=catalog_file_path, 
                            help=f'Output catalog file path (default: $CATALOG_FILE_PATH={catalog_file_path})')
    gen_parser.add_argument('--name', '-n', default='default', help='Catalog name')
    gen_parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing file')
    gen_parser.add_argument('--default-arch', default='x86_64', help='Default architecture')
    gen_parser.add_argument('--default-os', default='rhel', help='Default OS')
    gen_parser.add_argument('--default-os-version', default='10.0', help='Default OS version')
    gen_parser.add_argument('--schema', help='Schema file for validation')
    gen_parser.add_argument('--validate', action='store_true', default=True,
                            help='Validate after generation')
    gen_parser.set_defaults(func=cmd_generate)

    # Add command
    add_parser = subparsers.add_parser('add', help='Add packages to existing catalog')
    add_parser.add_argument('--input', '-i', help='Input file with packages to add')
    add_parser.add_argument('--catalog', '-c', default=catalog_file_path,
                            help=f'Existing catalog file (default: $CATALOG_FILE_PATH={catalog_file_path})')
    add_parser.add_argument('--output', '-o', help='Output file (default: overwrite catalog)')
    add_parser.add_argument('--default-arch', default='x86_64', help='Default architecture')
    add_parser.add_argument('--default-os', default='rhel', help='Default OS')
    add_parser.add_argument('--default-os-version', default='10.0', help='Default OS version')
    add_parser.add_argument('--schema', help='Schema file for validation')
    add_parser.add_argument('--validate', action='store_true', default=True,
                            help='Validate after add')
    add_parser.set_defaults(func=cmd_add)

    # Delete command
    del_parser = subparsers.add_parser('delete', help='Delete packages from catalog')
    del_parser.add_argument('--input', '-i', help='Input file with packages to delete')
    del_parser.add_argument('--catalog', '-c', default=catalog_file_path,
                            help=f'Existing catalog file (default: $CATALOG_FILE_PATH={catalog_file_path})')
    del_parser.add_argument('--output', '-o', help='Output file (default: overwrite catalog)')
    del_parser.add_argument('--schema', help='Schema file for validation')
    del_parser.add_argument('--validate', action='store_true', default=True,
                            help='Validate after delete')
    del_parser.set_defaults(func=cmd_delete)

    # Validate command
    val_parser = subparsers.add_parser('validate', help='Validate a catalog')
    val_parser.add_argument('--catalog', '-c', default=catalog_file_path,
                            help=f'Catalog file to validate (default: $CATALOG_FILE_PATH={catalog_file_path})')
    val_parser.add_argument('--schema', '-s', help='JSON schema file')
    val_parser.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    
    # Validate required arguments
    if args.command == 'generate':
        if not args.input:
            parser.error("generate: --input is required")
        if not args.output:
            parser.error("generate: --output is required (set CATALOG_FILE_PATH or use -o)")
    elif args.command in ('add', 'delete'):
        if not args.input:
            parser.error(f"{args.command}: --input is required")
        if not args.catalog:
            parser.error(f"{args.command}: --catalog is required (set CATALOG_FILE_PATH or use -c)")
    elif args.command == 'validate':
        if not args.catalog:
            parser.error("validate: --catalog is required (set CATALOG_FILE_PATH or use -c)")
    
    setup_logging(args.log_dir)

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
