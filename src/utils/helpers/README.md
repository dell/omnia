# Catalog Migration Utility

## Overview

The `catalog_migrate.sh` utility is designed to migrate catalog files from the deprecated `base_os` type to the standardized `baseos` type. This addresses GitHub issue #5240: https://github.com/dell/omnia/issues/5240

## Purpose

The Omnia codebase previously used inconsistent naming between `base_os` and `baseos` for catalog group types. This utility standardizes the naming to `baseos` to align with RHEL repository naming conventions (e.g., `baseos`, `appstream`).

## Usage

### Basic Usage

```bash
./src/utils/helpers/catalog_migrate.sh <catalog_file>
```

### Options

- `-b, --backup`: Create a backup of the original file before migration
- `-d, --dry-run`: Show what would be changed without making changes
- `-f, --force`: Force migration even if file already uses baseos
- `-h, --help`: Show help message
- `-v, --validate`: Validate catalog after migration (requires jq)

### Examples

#### Dry run to see what would change
```bash
./src/utils/helpers/catalog_migrate.sh --dry-run /path/to/catalog.json
```

#### Migrate with backup and validation
```bash
./src/utils/helpers/catalog_migrate.sh --backup --validate /path/to/catalog.json
```

#### Force migration (if already using baseos)
```bash
./src/utils/helpers/catalog_migrate.sh --force /path/to/catalog.json
```

## Migration Process

The utility performs the following steps:

1. **Validation**: Checks if the catalog file exists and is accessible
2. **Analysis**: Determines if the file contains `base_os` types
3. **Backup**: Creates a timestamped backup if requested
4. **Migration**: Replaces all instances of `"type": "base_os"` with `"type": "baseos"`
5. **Validation**: Validates the migrated JSON file if jq is available
6. **Rollback**: Restores from backup if validation fails

## Safety Features

- **Backup creation**: Always create backups before migration
- **Dry run mode**: Preview changes before applying them
- **JSON validation**: Ensures migrated files remain valid JSON
- **Automatic rollback**: Restores from backup if validation fails
- **Idempotent**: Safe to run multiple times on the same file

## Important Notes

### Breaking Change

This migration is a **breaking change**. Catalogs using the old `base_os` type will fail validation against the updated schema. All existing catalogs must be migrated before deploying the updated code.

### Schema Version

The catalog schema has been bumped to indicate this breaking change:
- **Repo Manager schema**: `schemaVersion` bumped from `2.0` → `2.1`
- **Image Build Manager schema**: `schemaVersion` bumped from `1.0` → `1.1`
- **Repo Manager RHEL schema**: `schemaVersion` bumped from `1.0` → `1.1`

Note: The legacy 1.0 schema (used for transformation) remains unchanged as it uses the old PascalCase format.

Users should be notified of the migration requirement before upgrading.

### Coordinated Deployment

This change requires coordinated deployment across all components that consume catalogs:
- Repo Manager
- Image Build Manager
- Build Stream
- Orchestrator

## Testing

The utility has been tested with:
- Catalogs using `base_os` type (successful migration)
- Catalogs already using `baseos` type (no-op with success)
- Invalid JSON files (error handling)
- Backup creation and restoration
- Dry run mode

## Troubleshooting

### jq not found

If you see warnings about `jq` not being found, JSON validation will be skipped. To enable validation:

```bash
# On RHEL/CentOS
sudo dnf install jq

# On Ubuntu/Debian
sudo apt-get install jq
```

### Migration fails

If migration fails:
1. Check the backup file (created with timestamp)
2. Review error messages for specific issues
3. Ensure the file is valid JSON before migration
4. Use dry-run mode to preview changes

## Related Files

- Schema: `src/repo_manager/schemas/catalog_schema.json`
- Issue: https://github.com/dell/omnia/issues/5240
- Related changes: Catalog type standardization across all domains

## Support

For issues or questions about this utility, please refer to the GitHub issue #5240 or contact the Omnia development team.
