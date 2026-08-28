# Content Configuration Guide

## Overview

The `software_config.json` file defines which software content to download and
make available through Pulp. It is the **primary configuration file** for content
management in Repo Manager.

**Location**: `input/project_default/software_config.json`

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `OMNIA_DATA_PATH` | Base directory for Omnia installation | `/opt/omnia` |
| `OMNIA_PROJECT_NAME` | Project name identifier | `project_default` |

Input and output paths can be customized using these environment variables for portability.

## File Structure

```json
{
  "software": [
    {
      "name": "slurm",
      "version": "24.05.4",
      "architectures": ["x86_64", "aarch64"],
      "type": "rpm",
      "enabled": true
    },
    {
      "name": "geopm",
      "version": "2.0.0",
      "architectures": ["x86_64"],
      "type": "tarball",
      "enabled": true,
      "source_url": "https://github.com/geopm/geopm"
    },
    {
      "name": "custom_python_module",
      "version": "1.0.0",
      "architectures": ["x86_64", "aarch64"],
      "type": "pip_module",
      "enabled": true,
      "pip_index": "https://pypi.org/simple"
    }
  ]
}
```

## Content Types

Repo Manager supports the following content types in `software_config.json`:

| Type | Description | Source |
|------|-------------|--------|
| `rpm` | RPM packages and repositories | RHEL/CentOS repositories, custom RPM repos |
| `tarball` | Container image tarballs | Docker images, Singularity images |
| `manifest` | Container manifests | Image manifests, signatures |
| `git` | Git repositories | Source code repositories |
| `pip_module` | Python packages | PyPI, custom Python package indexes |
| `iso` | ISO images | OS installation media |
| `shell` | Shell scripts | Installation scripts, utilities |
| `ansible_galaxy_collection` | Ansible collections | Ansible Galaxy, custom collections |

## Configuration Fields

### Common Fields (All Types)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Software name/identifier |
| `version` | string | Yes | Software version |
| `architectures` | array | Yes | Target architectures (`x86_64`, `aarch64`, or both) |
| `type` | string | Yes | Content type (see table above) |
| `enabled` | boolean | No | Whether to download this software (default: `true`) |

### Type-Specific Fields

#### RPM Type
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repo_name` | string | No | Custom repository name (defaults to name-based naming) |
| `gpg_check` | boolean | No | Enable GPG signature verification (default: `true`) |

#### Tarball/Manifest Type
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_url` | string | Yes | Source URL for the tarball/manifest |
| `registry_url` | string | No | Container registry URL |
| `image_tag` | string | No | Container image tag |

#### Git Type
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_url` | string | Yes | Git repository URL |
| `branch` | string | No | Git branch to clone (default: `main`) |
| `commit` | string | No | Specific commit hash (takes precedence over branch) |

#### Pip Module Type
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pip_index` | string | No | Custom PyPI index URL (default: PyPI) |
| `requirements_file` | string | No | Path to requirements.txt file |

#### ISO Type
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_url` | string | Yes | ISO file URL |
| `checksum` | string | No | Expected checksum for verification |

#### Shell Type
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_url` | string | Yes | Script file URL |
| `execution_mode` | string | No | Execution mode (`download_only` or `execute`) |

#### Ansible Galaxy Collection Type
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `collection_name` | string | Yes | Collection name in format `namespace.collection` |
| `galaxy_server` | string | No | Custom Galaxy server URL |
| `version` | string | No | Collection version (defaults to latest) |

## How It Works

```
software_config.json                repo_manager_config.yml
┌──────────────────────────┐          ┌──────────────────────────────────┐
│ software:                 │          │ user_repo_url_x86_64:           │
│   - name: slurm          │──┐       │   - name: custom_repo            │
│   - name: geopm          │  └──────▶│     url: http://...              │
└──────────────────────────┘          └──────────────────────────────────┘
                                              │
                              ┌───────────────┼───────────────┐
                              ▼                               ▼
                     Standard Repos                  User Repos
                     (from software_config)         (from config)
                              │                               │
                              ▼                               ▼
                         Pulp Distributions              Pulp Distributions
                              │                               │
                              └───────────────┬───────────────┘
                                              ▼
                                    repo_status.yml
```

1. `software_config.json` defines standard software to download
2. `repo_manager_config.yml` defines custom user repositories
3. Repo Manager downloads content from both sources into Pulp
4. `repo_status.yml` is generated with Pulp distribution URLs

## Customization

### Adding new software

Add to `software_config.json`:

```json
{
  "software": [
    {
      "name": "my_software",
      "version": "1.0.0",
      "architectures": ["x86_64"],
      "type": "rpm",
      "enabled": true
    }
  ]
}
```

### Enabling/disabling software

Set `enabled: false` to temporarily disable download:

```json
{
  "name": "optional_software",
  "version": "2.0.0",
  "architectures": ["x86_64", "aarch64"],
  "type": "pip_module",
  "enabled": false
}
```

### Adding custom user repositories

Add to `repo_manager_config.yml`:

```yaml
user_repo_url_x86_64:
  - name: "custom_rhel_repo"
    url: "http://my-repo.example.com/rhel10/"
  - name: "custom_epel_repo"
    url: "http://my-repo.example.com/epel10/"
```

## Architecture Support

Software can be configured for specific architectures:

```json
{
  "name": "architecture_specific",
  "version": "1.0.0",
  "architectures": ["x86_64"],        // Only x86_64
  "type": "rpm"
}
```

```json
{
  "name": "multi_arch",
  "version": "1.0.0",
  "architectures": ["x86_64", "aarch64"],  // Both architectures
  "type": "tarball"
}
```

## Download Concurrency

Download concurrency is configured through the repository configuration policy and caching policy settings. See the Policy Configuration section above for details on controlling synchronization behavior.

## Validation

The `software_config.json` is validated against a JSON schema at:
`plugins/module_utils/input_validation/schema/software_config.json`

Common validation errors:
- Missing required fields
- Invalid content type
- Invalid architecture specification
- Malformed JSON syntax

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

## Historical Context

In previous versions, software configuration used separate files per software
module. The current `software_config.json` consolidates all software definitions
into a single, validated configuration file that supports multiple content types
and architectures.
