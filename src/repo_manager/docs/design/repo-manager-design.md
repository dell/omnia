# Repo Manager Design Document

## Overview

Repo Manager is a content management system that deploys and manages Pulp for offline content distribution. It handles RPM repositories, container images, Python packages, and other content types for offline cluster deployments.

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Repo Manager                              │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Ansible    │    │    Pulp      │    │   Podman     │ │
│  │  Playbooks   │────│   Server     │────│  Containers  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                   │                   │           │
│         ▼                   ▼                   ▼           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ Custom       │    │   Content    │    │   System     │ │
│  │ Modules      │    │  Storage     │    │   Services   │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Ansible Playbooks**
   - Main orchestration layer
   - Tag-based execution (deploy, validate, download, status, cleanup)
   - Localhost-only execution

2. **Pulp Server**
   - Content management server
   - Supports RPM, file, and Python distributions
   - REST API for content operations

3. **Podman Containers**
   - Container runtime for Pulp services
   - Isolated deployment environment
   - Easy management and cleanup

4. **Custom Ansible Modules**
   - Pulp-specific operations
   - Content download and management
   - Status generation

## Design Principles

### 1. Localhost-Only Execution

**Rationale**: Simplify deployment, eliminate SSH dependencies

**Implementation**:
- All playbooks use `hosts: localhost`
- No remote execution required
- Simplified authentication

### 2. Tag-Based Execution

**Rationale**: Enable selective operations and debugging

**Implementation**:
```bash
ansible-playbook repo_manager.yml --tags deploy
ansible-playbook repo_manager.yml --tags download
ansible-playbook repo_manager.yml --tags status
```

### 3. Standard Plugin Structure

**Rationale**: Follow Ansible best practices

**Implementation**:
```
plugins/
├── callback/          # Output callbacks
├── modules/           # Custom modules
└── module_utils/      # Module utilities
```

### 4. Schema-Based Validation

**Rationale**: Ensure input configuration correctness

**Implementation**:
- JSON schemas for all input files
- Two-level validation (schema + logic)
- Clear error messages

### 5. System-Wide Pulp CLI

**Rationale**: Simplify Pulp operations across the system

**Implementation**:
- Symlink at `/usr/local/bin/pulp`
- Automatic setup during deployment
- Consistent access point

## Data Flow

### 1. Configuration Flow

```
Input Files
    ├── repo_manager_config.yml
    ├── software_config.json
    └── repo_manager_endpoint_config.json
         │
         ▼
    Validation
         │
         ▼
    Pulp Deployment
         │
         ▼
    Content Download
         │
         ▼
    Status Generation
         │
         ▼
    Output Files
    ├── repo_status.yml
    └── status.csv
```

### 2. Content Download Flow

```
software_config.json
         │
         ▼
    Task Generation
         │
         ▼
    Parallel Download
         │
         ├── RPM Repositories
         ├── Container Images
         ├── Python Packages
         ├── Git Repositories
         ├── ISO Images
         ├── Shell Scripts
         └── Ansible Collections
         │
         ▼
    Pulp Import
         │
         ▼
    Distribution Creation
```

## Module Design

### Custom Modules

#### generate_local_repo_access

**Purpose**: Generate repo_status.yml from Pulp distributions

**Input**:
- Pulp server configuration
- Cluster OS information
- Output path

**Output**: repo_status.yml file

**Key Features**:
- Queries Pulp for all distributions
- Maps repository names to URLs
- Handles both architectures
- Supports user repositories

#### pulp_cleanup

**Purpose**: Cleanup Pulp repositories and distributions

**Input**:
- Cleanup type (rpm, file, python)
- Distribution names

**Output**: Cleanup results

**Key Features**:
- Safe removal operations
- Dependency checking
- Status reporting

#### validate_input

**Purpose**: Validate input configuration files

**Input**:
- Configuration file paths
- Validation schemas

**Output**: Validation results

**Key Features**:
- Schema validation
- Logic validation
- Clear error messages

### Module Utilities

#### input_validation

**Purpose**: Input validation framework

**Components**:
- Schema validation engine
- Business logic validators
- Common validation functions

#### repo_manager

**Purpose**: Repo manager utilities

**Components**:
- Pulp command wrappers
- Download functions
- Metadata management
- Configuration handling

## Error Handling

### Error Categories

1. **Configuration Errors**
   - Invalid input files
   - Missing required fields
   - Schema violations

2. **Network Errors**
   - Download failures
   - Connection timeouts
   - DNS resolution issues

3. **System Errors**
   - Insufficient resources
   - Permission issues
   - Container failures

### Error Handling Strategy

1. **Fail-Fast for Configuration Errors**
   - Immediate validation
   - Clear error messages
   - No partial execution

2. **Retry for Transient Errors**
   - Network timeouts
   - Temporary service unavailability
   - Configurable retry limits

3. **Cleanup on Failure**
   - Partial downloads removed
   - Temporary files cleaned
   - System state restored

## Security Considerations

### 1. SSL/TLS Configuration

**Implementation**:
- HTTPS for Pulp API
- Certificate validation
- Self-signed certificate support

### 2. Credential Management

**Implementation**:
- Ansible Vault for secrets
- Environment variable support
- Secure credential storage

### 3. File Permissions

**Implementation**:
- Restrictive permissions for sensitive files
- Proper ownership
- Regular permission audits

## Performance Considerations

### 1. Parallel Downloads

**Implementation**:
- Configurable concurrency
- Parallel task execution
- Resource monitoring

### 2. Content Caching

**Implementation**:
- Pulp content caching
- Intelligent download skipping
- Metadata optimization

### 3. Resource Management

**Implementation**:
- Memory limits
- Disk space monitoring
- Container resource constraints

## Extensibility

### Adding New Content Types

1. Define content type in schema
2. Add download logic to modules
3. Update status generation
4. Add validation rules

### Adding New Validation Rules

1. Update JSON schema
2. Add validator function
3. Register in validation engine
4. Add error messages

## Testing Strategy

### 1. Unit Testing

- Custom module testing
- Utility function testing
- Schema validation testing

### 2. Integration Testing

- Pulp deployment testing
- Content download testing
- Status generation testing

### 3. End-to-End Testing

- Full workflow testing
- Error scenario testing
- Performance testing

## Future Enhancements

### Planned Features

1. **Multi-Pulp Support**
   - Support for multiple Pulp instances
   - Content federation
   - Load balancing

2. **Advanced Scheduling**
   - Scheduled content updates
   - Incremental downloads
   - Change detection

3. **Enhanced Monitoring**
   - Metrics collection
   - Performance monitoring
   - Alerting integration

4. **Content Signing**
   - GPG signing for RPMs
   - Container image signing
   - Signature verification

## Dependencies

### External Dependencies

- Ansible Core
- Podman
- Python 3
- Pulp (via containers)

### Internal Dependencies

- Omnia base libraries
- Common validation framework
- Shared utilities

## Documentation

### User Documentation

- Architecture overview
- Configuration guide
- Troubleshooting guide
- API reference

### Developer Documentation

- Module development guide
- Contribution guidelines
- Code structure
- Testing guidelines

## Maintenance

### Regular Maintenance Tasks

1. **Content Updates**
   - Regular repository synchronization
   - Security patch updates
   - Content validation

2. **System Maintenance**
   - Log rotation
   - Disk space management
   - Certificate renewal

3. **Monitoring**
   - Service health checks
   - Performance monitoring
   - Capacity planning
