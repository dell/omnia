# image_build_setup

Setup role that runs first under the `always` tag. It resolves environment and
project paths, creates runtime directories, validates tags, loads the image
configuration, and conditionally validates/parses `repo_status.yml`.

## What It Does

1. Validates requested top-level tags and rejects unsupported combinations.
2. Resolves required environment variables and project/runtime directories.
3. Checks the runtime project input directory. The normal `domain-init.sh`
   staging step copies the repository's flat input templates there; the role's
   fallback copy applies only if a project-specific source directory exists.
4. Loads `image_build_config.yml` except for cleanup and precheck flows.
5. For build/execute/default flow, requires `repo_status.yml` plus the selected
   package source (`package_groups.yml` or `CATALOG_FILE_PATH`).
6. Validates current-format `repo_status.yml`, parses it through
   `omnia.image_build.parse_repo_status`, and checks repository URL reachability.
7. Sets initial OS facts (`cluster_os_type`, `cluster_os_version`, `repo_port`) from `repo_status.yml`
   - **Note**: `cluster_os_type` and `cluster_os_version` may be overridden downstream by
     `fetch_build_packages` from catalog baseos group or `package_groups.yml` OS metadata
8. Builds per-architecture repo lists (`repo_manager_repos_x86_64`, `repo_manager_repos_aarch64`).
9. Validates the repo manager certificate when a path is supplied and sets S3 endpoint facts.

`repo_status.yml` is not required for `validate`, `credentials`, `prepare`,
`precheck`, `cleanup`, or `cleanup_images`. Input schema/logic validation is
performed by the separate `validate_image_build_input` role.

## Requirements

- Valid `omnia.env` sourced (system environment variables)
- Python 3.12+, Ansible 2.20+

## Modules Used

| Module | Purpose |
|--------|---------|
| `validate_repo_status_contract` | Enforces the current `repositories`-based upstream contract |
| `parse_repo_status` | Extracts OS version, repo port, certificate path, and per-architecture repository lists |

## Role Variables

See `vars/main.yml`; this role has no `defaults/main.yml`.

## Dependencies

None (this is the first role to run).

## Example

```yaml
- hosts: localhost
  roles:
    - image_build_setup
```
