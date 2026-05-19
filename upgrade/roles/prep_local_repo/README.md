# prep_local_repo Role

## Purpose

Prepares local repository for software upgrades by creating a staging directory with modified configurations and syncing packages for target versions.

## Key Design Principles

1. **No JSON Artifacts** - Reads JSON files from actual `/opt/omnia/input/project_default/config/` directory
2. **Staging Directory** - Creates temporary copies of already-updated `software_config.json` and merged `local_repo_config.yml`
3. **Source of Truth** - `upgrade_manifest.yml` defines upgrade paths and enabled components
4. **Only repos.yml** - Maintains upgrade-specific repositories in `upgrade/artifacts/repos.yml`
5. **Read-Only Input** - Does NOT modify files in `/opt/omnia/input/project_default/` (those are updated by `manage_upgrade_inputs` role)

## Workflow

```
1. Validate prerequisites
   - Verify software_config.json exists in /opt/omnia/input/project_default/
   - Verify JSON files exist for all hop target versions
2. Create staging directory (/tmp/upgrade_local_repo_XXXXX/)
   - Copy software_config.json from /opt/omnia/input/project_default/ (already updated with target versions)
   - Copy local_repo_config.yml from /opt/omnia/input/project_default/ and merge with upgrade repos from repos.yml
   - Copy versioned JSON files from /opt/omnia/input/project_default/config/ for all hop targets
3. Sync local repository
   - Temporarily set input_project_dir to staging directory
   - Run validation role
   - Run parse_and_download role
   - Restore original input_project_dir
4. Cleanup staging directory
```

**Note**: The `manage_upgrade_inputs` role updates `software_config.json` with target versions BEFORE this role executes. This role only copies the already-updated configuration to staging.

## Files

- `tasks/main.yml` - Entry point
- `tasks/load_upgrade_config.yml` - Load and validate upgrade_config.yml
- `tasks/validate_prerequisites.yml` - Validate versions and JSON files
- `tasks/create_staging.yml` - Create staging directory with merged configs
- `tasks/sync_local_repo.yml` - Run local_repo roles

## Required Variables

- `input_project_dir` - Path to input directory
- `upgrade_active_architectures` - List of architectures (default: ['x86_64'])

## Usage

```yaml
- name: Prepare local repository for upgrade
  ansible.builtin.include_role:
    name: prep_local_repo
  vars:
    input_project_dir: "{{ playbook_dir }}/../input"
```

## Staging Directory Structure

```
/tmp/upgrade_local_repo_XXXXX/
├── software_config.json      # Copied from /opt/omnia/input/project_default/ (already contains target versions)
├── local_repo_config.yml     # Copied from /opt/omnia/input/project_default/ and merged with repos.yml
└── config/
    └── x86_64/
        └── rhel/
            └── 10.0/
                ├── service_k8s_v1.35.1.json  # Copied from /opt/omnia/input/project_default/config/
                ├── default_packages.json     # Copied from /opt/omnia/input/project_default/config/
                └── ...
```

**Important**: All files in staging are COPIES from `/opt/omnia/input/project_default/`. The staging directory is temporary and deleted after package synchronization.

## JSON File Naming Convention

JSON files for versioned components use the format: `<component>_v<version>.json`

Examples:
- `service_k8s_v1.35.1.json` - Kubernetes service packages for version 1.35.1
- `service_k8s_v1.36.1.json` - Kubernetes service packages for version 1.36.1

## Difference from Reference Codebase

The reference codebase (`sudha_k8s-upgrade_new`) uses JSON artifacts stored in `upgrade/artifacts/service_k8s/v1.35.1/`. This implementation:

- **Does NOT use JSON artifacts** - reads from actual input directory
- **Only maintains repos.yml** - for upgrade-specific repository URLs
- **Uses staging directory** - actual copies, no symlinks
- **Simpler structure** - no platform-encoded filenames needed
