#!/bin/bash
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

set -euo pipefail

# Script to migrate catalog files from base_os to baseos type
# Addresses GitHub issue #5240: https://github.com/dell/omnia/issues/5240

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] <catalog_file>

Migrate catalog files from base_os to baseos type.

Arguments:
    catalog_file          Path to the catalog JSON file to migrate

Options:
    -b, --backup          Create backup of original file before migration
    -d, --dry-run         Show what would be changed without making changes
    -f, --force           Force migration even if file already uses baseos
    -h, --help            Show this help message
    -v, --validate        Validate catalog after migration (requires jq)

Examples:
    $0 /path/to/catalog.json
    $0 --backup /path/to/catalog.json
    $0 --dry-run /path/to/catalog.json
    $0 --backup --validate /path/to/catalog.json

EOF
}

# Function to check if jq is available
check_jq() {
    if ! command -v jq &> /dev/null; then
        print_warning "jq not found. JSON validation will be skipped."
        return 1
    fi
    return 0
}

# Function to validate JSON file
validate_json() {
    local file="$1"
    if check_jq; then
        if jq empty "$file" 2>/dev/null; then
            print_success "JSON validation passed for $file"
            return 0
        else
            print_error "JSON validation failed for $file"
            return 1
        fi
    else
        print_warning "Skipping JSON validation (jq not available)"
        return 0
    fi
}

# Function to check if catalog uses base_os
check_base_os() {
    local file="$1"
    if grep -q '"type": "base_os"' "$file"; then
        return 0
    else
        return 1
    fi
}

# Function to check if catalog already uses baseos
check_baseos() {
    local file="$1"
    if grep -q '"type": "baseos"' "$file"; then
        return 0
    else
        return 1
    fi
}

# Function to perform migration
migrate_catalog() {
    local file="$1"
    local backup="$2"
    local dry_run="$3"
    local validate="$4"

    print_info "Processing catalog: $file"

    # Check if file exists
    if [[ ! -f "$file" ]]; then
        print_error "File not found: $file"
        return 1
    fi

    # Check if file already uses baseos
    if check_baseos "$file"; then
        if [[ "$force" == "true" ]]; then
            print_warning "File already uses baseos, but forcing migration as requested"
        else
            print_success "File already uses baseos, no migration needed"
            return 0
        fi
    fi

    # Check if file uses base_os
    if ! check_base_os "$file"; then
        print_info "File does not contain base_os type, no migration needed"
        return 0
    fi

    # Create backup if requested
    if [[ "$backup" == "true" ]]; then
        local backup_file="${file}.backup.$(date +%Y%m%d_%H%M%S)"
        print_info "Creating backup: $backup_file"
        if [[ "$dry_run" == "false" ]]; then
            cp "$file" "$backup_file"
            print_success "Backup created successfully"
        else
            print_info "[DRY RUN] Would create backup: $backup_file"
        fi
    fi

    # Perform migration
    print_info "Migrating base_os to baseos in $file"
    
    if [[ "$dry_run" == "false" ]]; then
        # Perform the actual replacement
        sed -i 's/"type": "base_os"/"type": "baseos"/g' "$file"
        print_success "Migration completed"
    else
        print_info "[DRY RUN] Would replace 'base_os' with 'baseos' in $file"
        # Show what would change
        print_info "Changes that would be made:"
        grep -n '"type": "base_os"' "$file" || print_info "No base_os found (already migrated)"
    fi

    # Validate after migration if requested
    if [[ "$validate" == "true" && "$dry_run" == "false" ]]; then
        print_info "Validating migrated catalog..."
        if validate_json "$file"; then
            print_success "Migrated catalog is valid JSON"
        else
            print_error "Migrated catalog failed JSON validation"
            if [[ "$backup" == "true" ]]; then
                print_info "Restoring from backup: $backup_file"
                cp "$backup_file" "$file"
                print_warning "File restored from backup due to validation failure"
            fi
            return 1
        fi
    fi

    return 0
}

# Main function
main() {
    local backup=false
    local dry_run=false
    local force=false
    local validate=false
    local catalog_file=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -b|--backup)
                backup=true
                shift
                ;;
            -d|--dry-run)
                dry_run=true
                shift
                ;;
            -f|--force)
                force=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            -v|--validate)
                validate=true
                shift
                ;;
            -*)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                catalog_file="$1"
                shift
                ;;
        esac
    done

    # Check if catalog file is provided
    if [[ -z "$catalog_file" ]]; then
        print_error "No catalog file specified"
        usage
        exit 1
    fi

    # Convert to absolute path if relative
    if [[ ! "$catalog_file" = /* ]]; then
        catalog_file="$(cd "$(dirname "$catalog_file")" && pwd)/$(basename "$catalog_file")"
    fi

    print_info "Catalog Migration Utility"
    print_info "Target file: $catalog_file"
    print_info "Backup: $backup"
    print_info "Dry run: $dry_run"
    print_info "Force: $force"
    print_info "Validate: $validate"
    echo ""

    # Perform migration
    if migrate_catalog "$catalog_file" "$backup" "$dry_run" "$validate"; then
        print_success "Migration completed successfully"
        exit 0
    else
        print_error "Migration failed"
        exit 1
    fi
}

# Run main function
main "$@"
