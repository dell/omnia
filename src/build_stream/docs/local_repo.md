# Local Repository

The Local Repository workflow manages the creation and configuration of local package repositories for the Omnia platform.

## What It Does

The Local Repository workflow provides:
- Local package repository setup and configuration
- Package synchronization from remote sources
- Repository metadata generation and management
- Integration with Pulp for repository management
- Repository validation and health checking

## Inputs/Outputs

**Inputs:**
- Package lists from catalog processing
- Repository configuration parameters
- Remote repository URLs and credentials
- Storage and bandwidth constraints

**Outputs:**
- Configured local repositories
- Synchronized package metadata
- Repository access credentials
- Health check reports and validation results

## Key Logic Locations

**Primary Files:**
- `api/local_repo/routes.py` - HTTP endpoints for repository operations
- `orchestrator/local_repo/use_cases/create_local_repo.py` - Repository creation logic
- `core/localrepo/entities.py` - Repository domain entities
- `core/localrepo/repositories.py` - Repository data access
- `core/localrepo/services.py` - Repository management services

**Main Components:**
- **CreateLocalRepoUseCase** - Handles repository creation and setup
- **LocalRepoService** - Repository management and operations
- **LocalRepoRepository** - Repository configuration persistence
- **PackageSyncService** - Package synchronization from remote sources

## Workflow Flow

1. **Repository Request**: Client submits repository creation request
2. **Configuration Validation**: Repository parameters validated
3. **Remote Source Setup**: Remote repository connections configured
4. **Package Synchronization**: Packages synced from remote sources
5. **Metadata Generation**: Repository metadata created and updated
6. **Access Configuration**: User access and permissions configured
7. **Health Validation**: Repository health and accessibility validated
8. **Registration**: Repository registered with downstream systems

## Repository Types

Supports multiple repository types:
- **YUM/DNF repositories** - RPM-based package management
- **APT repositories** - Debian-based package management
- **Python repositories** - PyPI-compatible package hosting
- **Custom repositories** - Organization-specific package formats

## Integration Points

- Receives package lists from catalog workflow
- Provides packages to image building workflow
- Integrates with validation workflow for quality checks
- Uses Vault for secure credential storage
- Connects to Pulp for advanced repository management

## Configuration

Repository configuration includes:
- Storage locations and quotas
- Remote source URLs and credentials
- Synchronization schedules and policies
- Access control and permissions
- Health check parameters

## Security

- Secure credential management through Vault
- Access control based on user roles
- Package signature verification
- Audit logging for all repository operations

## Error Handling

- Graceful handling of remote source failures
- Retry mechanisms for synchronization errors
- Detailed error reporting and diagnostics
- Rollback capabilities for failed operations

## Monitoring

- Repository health status monitoring
- Package synchronization progress tracking
- Storage usage and quota monitoring
- Access logging and audit trails

## Performance Optimization

- Incremental synchronization to minimize bandwidth
- Parallel package downloading
- Caching of repository metadata
- Optimized storage layouts for fast access
