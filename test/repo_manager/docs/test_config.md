# Test Configuration

The `test_config.yml` file configures the test environment.

## Key Settings

- `oim_server_ip`: Target server IP (empty for local mode)
- `dataset`: Dataset to use (e.g., `data_set_01`)
- `project_name`: Project name (default: `project_default`)
- `report_path`: Path for test reports (default: `/opt/omnia/reports`)
- `sync_repo_manager_input`: Synchronize the selected public input files

The selected dataset is validated at pytest startup. A named dataset must be a
safe direct child of `datasets/` and must contain both
`input/repo_manager_config.yml` and
`input/repo_manager_endpoint_config.yml`. Symlinks, invalid YAML, and
credential-like files fail closed before synchronization.

With `dataset: ""`, verification uses the target's deployed configuration.
When input synchronization is explicitly enabled, the canonical public source
files are used as the synchronization source. Credentials are always managed
separately on the target.
