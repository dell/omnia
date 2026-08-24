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

| Variable | Purpose | Example |
|----------|---------|---------|
| `OMNIA_BASE_DIR` | Base directory for Omnia installation | `/opt/omnia` |
| `REPO_MANAGER_BASE_DIR` | Base directory for repo manager | `/opt/omnia/repo_manager` |
| `PYTHONPATH` | Python module search path | `/root/oim-multi-repo/omnia/src/repo_manager` |

### Optional Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `http_proxy` | HTTP proxy for downloads | `http://proxy.example.com:8080` |
| `https_proxy` | HTTPS proxy for downloads | `http://proxy.example.com:8080` |
| `no_proxy` | No proxy for these hosts | `localhost,127.0.0.1` |

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

```
/opt/omnia/input/project_default/
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
