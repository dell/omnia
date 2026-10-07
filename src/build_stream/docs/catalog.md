# Catalog Processing

The Catalog workflow handles software catalog parsing and role generation for the Omnia platform.

## What It Does

The Catalog workflow provides:
- Software catalog parsing from JSON files
- Role generation based on catalog contents
- Package categorization and dependency resolution
- Integration with Ansible for role creation
- Validation of catalog structure and contents

## Inputs/Outputs

**Inputs:**
- Software catalog JSON files
- Package configuration mappings
- Role templates and definitions
- Platform-specific parameters

**Outputs:**
- Generated Ansible roles
- Package dependency mappings
- Validated catalog structures
- Role metadata and documentation

## Key Logic Locations

**Primary Files:**
- `api/parse_catalog/routes.py` - Catalog parsing endpoints
- `orchestrator/catalog/use_cases/parse_catalog.py` - Catalog parsing logic

**Main Components:**
- **ParseCatalogUseCase** - Handles catalog parsing and validation
- **CatalogRepository** - Catalog data persistence

The `/catalog/roles` API and the `generate-input-files` stage were retired
in Omnia 2.3; each domain now consumes the catalog directly.

## Workflow Flow

1. **Catalog Upload**: Client submits catalog via `/api/v1/parse_catalog` endpoint
2. **Structure Validation**: Catalog schema and structure validated
3. **Package Parsing**: Individual packages extracted and categorized
4. **Dependency Resolution**: Package dependencies analyzed and resolved
5. **Role Generation**: Ansible roles generated based on packages
6. **Input File Creation**: Configuration files created for downstream workflows
7. **Validation**: Generated artifacts validated for completeness
8. **Storage**: Results stored in artifact repository

## Package Categorization

Packages are categorized into:
- **Base OS Bundles**: Operating system packages (e.g., rhel)
- **Driver Bundles**: Hardware driver packages (e.g., nvidia_gpu_driver)
- **Functional Bundles**: Core service packages (service_k8s, slurm_custom, additional_packages)
- **Infrastructure Bundles**: CSI and infrastructure packages (csi_driver_powerscale)
- **Miscellaneous**: Additional packages that don't fit other categories

## Integration Points

- Feeds into local repository creation workflow
- Provides input for image building workflows
- Integrates with validation workflow for quality checks
- Uses Vault for secure access to package repositories

## Configuration

Catalog processing is configured through:
- Package mapping files
- Adapter policy configurations
- Validation rules and schemas
