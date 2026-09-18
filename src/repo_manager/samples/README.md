# Repo Manager Sample Input Files

This directory contains sample input configuration files for the repo_manager domain.

## Sample Files

### repo_manager_config.yml.sample
Sample repository manager configuration file showing the structure and available options.

### repo_manager_endpoint_config.yml.sample
Sample endpoint configuration file for Pulp server settings.

## Usage

To use these samples:

1. Copy the sample file to your project input directory:
   ```bash
   cp samples/repo_manager_config.yml.sample /opt/omnia/repo_manager/input/project_default/repo_manager_config.yml
   ```

2. Edit the copied file to match your environment and requirements.

3. Validate the configuration:
   ```bash
   ansible-playbook playbooks/validate/validate_config.yml
   ```

## Configuration Options

### repo_manager_config.yml

- **cluster_os_type**: Operating system type (default: "rhel")
- **cluster_os_version**: OS version (default: "10.0")
- **repositories**: Repository configuration for different architectures
- **user_repo_url_x86_64**: Custom x86_64 repository URLs
- **user_repo_url_aarch64**: Custom aarch64 repository URLs
- **additional_repos_x86_64**: Additional x86_64 repositories
- **additional_repos_aarch64**: Additional aarch64 repositories

### repo_manager_endpoint_config.yml

- **pulp_server_port**: Pulp server port (default: 2225)
- **pulp_server_ip**: Optional endpoint IP; defaults to `SYSTEM_ADMIN_NIC_IPV4`
- HTTPS is mandatory; certificate paths are generated from the runtime data path

## Notes

- These are sample files only - modify them according to your requirements
- Ensure all paths use the OMNIA_DATA_PATH environment variable for portability
- Validate configurations before running repo_manager operations
- Keep sensitive information (passwords, keys) secure
