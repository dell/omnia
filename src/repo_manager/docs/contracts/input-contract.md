# Input Contract

## Overview

This document defines the input files and configurations required by Repo Manager
to deploy Pulp, download content, and generate repository status files.

## Required Input Files

### 1. repo_manager_config.yml

**Location**: `input/project_default/repo_manager_config.yml`

**Purpose**: Main configuration file for repository manager settings

**Required Fields**:

```yaml
# Pulp server configuration
pulp_server_ip: "192.168.1.100"
pulp_server_port: 24817
pulp_protocol: "https"

# Cluster OS configuration
cluster_os_type: "rhel"
cluster_os_version: "10.0"

# Output configuration (optional - defaults to {{ output_project_dir }})
# repo_manager_output_path: "{{ output_project_dir }}"

# User repositories (optional)
user_repo_url_x86_64:
  - name: "custom_repo"
    url: "http://custom-repo.example.com/rhel10/"

user_repo_url_aarch64:
  - name: "custom_repo"
    url: "http://custom-repo.example.com/rhel10-aarch64/"
```

**Validation**: Validated against JSON schema at
`plugins/module_utils/input_validation/schema/repo_manager_config.json`

### 2. software_config.json

**Location**: `input/project_default/software_config.json`

**Purpose**: Defines software content to download and manage in Pulp

**Required Structure**:

```json
{
  "software": [
    {
      "name": "software_name",
      "version": "1.0.0",
      "architectures": ["x86_64", "aarch64"],
      "type": "rpm|tarball|manifest|git|pip_module|iso|shell|ansible_galaxy_collection",
      "enabled": true
    }
  ]
}
```

**Validation**: Validated against JSON schema at
`plugins/module_utils/input_validation/schema/software_config.json`

### 3. repo_manager_endpoint_config.json

**Location**: `input/project_default/repo_manager_endpoint_config.json`

**Purpose**: Configuration for service endpoints and external connections

**Required Structure**:

```json
{
  "endpoints": {
    "pulp_api": "http://localhost:24817",
    "pulp_content": "http://localhost:24816"
  },
  "credentials": {
    "pulp_username": "admin",
    "pulp_password": "password"
  }
}
```

**Validation**: Validated against JSON schema at
`plugins/module_utils/input_validation/schema/repo_manager_endpoint_config.json`

## Optional Input Files

### 1. Credential Rules

**Location**: `plugins/module_utils/input_validation/schema/credential_rules.json`

**Purpose**: Defines credential validation rules for external services

### 2. Custom Validation Schemas

**Location**: `plugins/module_utils/input_validation/schema/`

**Purpose**: Custom JSON schemas for additional validation requirements

## Environment Variables

### Required Environment Variables

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `OMNIA_DATA_PATH` | Base directory for Omnia installation | `/opt/omnia` | `/custom/omnia` |
| `OMNIA_PROJECT_NAME` | Project name identifier | `project_default` | `my_project` |

### Optional Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `https_proxy` | HTTPS proxy for downloads | `https://proxy.example.com:8080` |
| `no_proxy` | No proxy for these hosts | `localhost,127.0.0.1` |

## Policy Configuration

### Repository Configuration Policy

Controls how repositories are configured and processed:

```yaml
repo_config: "partial"  # Options: always | partial
```

- `always`: Always configure all repositories regardless of existing state
- `partial`: Only configure repositories that are not already configured

### Caching Policy

Controls content synchronization behavior:

```yaml
caching_policy: true    # Options: true (on_demand) | false (immediate)
# Note: Per-repo 'caching' field overrides global caching_policy when set
```

- `true` (on_demand): Content is synchronized only when needed
- `false` (immediate): Content is always synchronized immediately

### Additional Repositories

Additional repository configurations:

```yaml
additional_repos:
  custom_repo:
    url: "http://custom-repo.example.com/rhel10/"
    caching: false  # Override global caching_policy
```

### User Repositories

User-defined repository configurations:

```yaml
user_repos:
  custom_rhel_repo:
    url: "http://my-repo.example.com/rhel10/"
```

### Policy Prioritization

Repository policies are prioritized in the following order:

1. Per-repo `caching` field (highest priority)
2. Global `caching_policy` setting
3. Default behavior based on `repo_config` setting

Example:
```yaml
# Global policy
caching_policy: true  # on_demand by default

# Per-repo override
additional_repos:
  custom_repo:
    url: "http://custom-repo.example.com/rhel10/"
    caching: false  # This repo uses immediate sync, overriding global policy
```

## Input Validation Process

### 1. Schema Validation (L1)

- Validates JSON/YAML structure against schemas
- Checks required fields and data types
- Validates enum values and formats

### 2. Logic Validation (L2)

- Validates business logic and dependencies
- Checks URL accessibility
- Validates subscription status
- Verifies file system paths

### 3. Runtime Validation

- Validates runtime dependencies
- Checks system resources
- Verifies network connectivity

## Input File Locations

### Development Environment

```
/root/oim-multi-repo/omnia/src/repo_manager/
├── input/
│   └── project_default/
│       ├── repo_manager_config.yml
│       ├── software_config.json
│       └── repo_manager_endpoint_config.json
```

### Production Environment

Input file locations can be customized using the `OMNIA_DATA_PATH` environment variable:

```
$OMNIA_DATA_PATH/repo_manager/input/$OMNIA_PROJECT_NAME/
├── repo_manager_config.yml
├── software_config.json
└── repo_manager_endpoint_config.json
```

Default production paths (when environment variables are not set):
```
/opt/omnia/repo_manager/input/project_default/
├── repo_manager_config.yml
├── software_config.json
└── repo_manager_endpoint_config.json
```

## Input Validation Errors

### Common Validation Failures

| Error | Cause | Fix |
|-------|-------|-----|
| `Required field missing` | Missing required field in config | Add the required field |
| `Invalid URL format` | Malformed URL | Fix URL format |
| `Invalid architecture` | Invalid architecture specified | Use `x86_64` or `aarch64` |
| `File not found` | Referenced file doesn't exist | Create or copy the file |
| `Schema validation failed` | JSON/YAML structure invalid | Fix structure according to schema |

## Input File Examples

### Minimal repo_manager_config.yml

```yaml
pulp_server_ip: "192.168.1.100"
pulp_server_port: 24817
pulp_protocol: "https"
cluster_os_type: "rhel"
cluster_os_version: "10.0"
# repo_manager_output_path: "{{ output_project_dir }}"  # Optional - defaults to {{ output_project_dir }}
```

### repo_manager_config.yml with Policy Configuration

```yaml
pulp_server_ip: "192.168.1.100"
pulp_server_port: 24817
pulp_protocol: "https"
cluster_os_type: "rhel"
cluster_os_version: "10.0"

# Policy Configuration
repo_config: "partial"  # Options: always | partial
caching_policy: true    # Options: true (on_demand) | false (immediate)

# Additional Repositories
additional_repos:
  custom_repo:
    url: "http://custom-repo.example.com/rhel10/"
    caching: false  # Override global caching_policy

# User Repositories
user_repos:
  custom_rhel_repo:
    url: "http://my-repo.example.com/rhel10/"
```

### Minimal software_config.json

```json
{
  "software": [
    {
      "name": "example_software",
      "version": "1.0.0",
      "architectures": ["x86_64"],
      "type": "rpm",
      "enabled": true
    }
  ]
}
```

## Input File Permissions

**Recommended Permissions**:
- Config files: `644` (rw-r--r--)
- Input directory: `755` (rwxr-xr-x)

**Owner**: `root:root` (or appropriate system user)

## Input File Backup

It is recommended to maintain backup copies of input files:

```bash
cp input/project_default/repo_manager_config.yml input/project_default/repo_manager_config.yml.backup
cp input/project_default/software_config.json input/project_default/software_config.json.backup
```

## Input File Version Control

Input files should be version controlled to track changes:
- Use Git for version control
- Commit changes with descriptive messages
- Tag releases for production deployments
