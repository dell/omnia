"""
Module to parse software_config.json data and download packages.
"""
import json
import os
import yaml
import common_utility
import download_common
import download_image
import download_rpm
import download_deb

def load_user_json(file_path):
    """
    Load software_config JSON data from file.

    Args:
        file_path: Path to the software_config.json file.
    """

    with open(file_path, 'r', encoding='utf-8') as user_file:
        user_data = json.load(user_file)
    return user_data

def load_repo_config_yaml(file_path):
    """
    Load repository configuration YAML data from file.

    Args:
        file_path: Path to the local_repo_config.yaml file.
    """

    with open(file_path, 'r', encoding='utf-8') as repo_config_file:
        repo_config_data = yaml.safe_load(repo_config_file)
    return repo_config_data

def load_software_config_json(software_names, cluster_os_type, cluster_os_version, user_json_path):
    """
    Load software configuration JSON files.

    Args:
        software_names: List of software names.
        cluster_os_type: Cluster OS type.
        cluster_os_version: Cluster OS version.
        user_json_path: Path to the software_config.json file.
    """
    software_configs = {}
    user_json_dir = os.path.dirname(user_json_path)
    for software_name in software_names:
        json_file_path = f'{user_json_dir}/config/{cluster_os_type}/{cluster_os_version}/{software_name}.json'
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r', encoding='utf-8') as json_file:
                software_config = json.load(json_file)
                software_configs[software_name] = software_config
    return software_configs


# Example function to process a package
def process_package(package, repo_store_path,status_file_path,cluster_os_type, cluster_os_version, repo_config, version_variables, nerdctl_registry_host, user_registries, cluster_name, software_names):
    """
    Function to process a package
    Args:
        package: The package information dictionary.
        repo_store_path: Path to the repository store.
        status_file_path: The path to the status file.
        cluster_os_type: Cluster OS type.
        cluster_os_version: Cluster OS version.
        repo_config: Repository configuration.
        version_variables: Variables for rendering version template.
        nerdctl_registry_host: Nerdctl registry host.     
    """
    package_name = package['package']
    package_type = package['type']
    print(f"Processing Package: {package_name}, Type: {package_type}")

    # Type-specific processing based on the extracted type
    process_by_package_type(package_name, package_type, package, repo_store_path, status_file_path, cluster_os_type, cluster_os_version, repo_config, version_variables, nerdctl_registry_host, user_registries, cluster_name, software_names)

# Type-specific processing function
def process_by_package_type(package_name, package_type, package, repo_store_path, status_file_path, cluster_os_type, cluster_os_version, repo_config, version_variables, nerdctl_registry_host, user_registries, cluster_name, software_names):
    """
    Function to process based on package type
    Args:
        package_name: The package name
        package_type: The package type
        package: The package information dictionary.
        repo_store_path: Path to the repository store.
        status_file_path: The path to the status file.
        cluster_os_type: Cluster OS type.
        cluster_os_version: Cluster OS version.
        repo_config: Repository configuration.
        version_variables: Variables for rendering version template.
        nerdctl_registry_host: Nerdctl registry host.
        user_registries: External registries hosted by user.
    """
    if package_type == 'rpm' and cluster_os_type in ['rhel','rocky']:
        download_rpm.process_rpm_package(package, repo_store_path, status_file_path, cluster_os_type, cluster_os_version, repo_config, version_variables, cluster_name)
    elif package_type == 'deb' and cluster_os_type == 'ubuntu':
        download_deb.process_deb_package(package, repo_store_path, status_file_path, cluster_os_type, cluster_os_version, repo_config, version_variables, cluster_name)
    elif package_type == 'pip_module':
        download_common.process_pip_package(package, repo_store_path, status_file_path)
    elif package_type == 'git':
        download_common.process_git_package(package, repo_store_path, status_file_path)
    elif package_type == 'tarball':
        download_common.process_tarball_package(package, repo_store_path, status_file_path, version_variables)
    elif package_type == 'manifest':
        download_common.process_manifest_package(package, repo_store_path, status_file_path)
    elif package_type == 'shell':
        download_common.process_shell_package(package, repo_store_path, status_file_path)
    elif package_type == 'image':
        download_image.process_image_package(package, repo_config, nerdctl_registry_host, status_file_path, version_variables, user_registries, software_names)
    elif package_type == 'ansible_galaxy_collection':
        download_common.process_ansible_galaxy_collection(package, repo_store_path, status_file_path)
    elif package_type == 'iso':
        download_common.process_iso_package(package, repo_store_path, status_file_path, cluster_os_type, cluster_os_version, repo_config, version_variables)
    else:
        print(f"Unknown package type: {package_type} for package {package_name}")


def main():
    """
    Main function to parse software_config.json data and initiate package downloads.
    """
    # File paths
    # Access environment variables
    user_json_path = os.environ.get('USER_JSON_PATH')
    local_repo_config_yaml_path = os.environ.get('LOCAL_REPO_CONFIG_YAML_PATH')
    status_file_path = os.environ.get('STATUS_FILE_PATH')
    nerdctl_registry_host = os.environ.get('NERDCTL_REGISTRY_HOST')
    software_name = os.environ.get('SOFTWARE_NAME')

    # Load data from software_config.json
    user_data = load_user_json(user_json_path)
    
    # Get the list of keys
    software_config_keys = user_data.keys()

    # Load data from local_repo_config.yml
    repo_config_data = load_repo_config_yaml(local_repo_config_yaml_path)

    version_variables = {}
    software_names = []

    # Iterate through 'softwares'
    for software in user_data.get('softwares', []):
        name = software.get('name')
        if name == software_name:
            software_names.append(name)

        # Check if 'version' key exists
        if 'version' in software:
            version = software['version']
            version_variables[f"{name}_version"] = version

    # Find the common keys between software_names and key_value_pairs
    subgroup_keys = set(software_names).intersection(software_config_keys)
   
    # Get the list of names for each subgroup key
    subgroup_names = []
    for key in subgroup_keys:
        subgroup_names.extend([item['name'] for item in user_data[key]])
    # Get the complete list of software names with subgroup
    subgroup_names.extend(software_names)

    # Iterate through subgroup keys
    for key in subgroup_keys:
        for item in user_data.get(key, []):
            name = item.get('name')

            # Check if 'version' key exists
            if 'version' in item:
                version = item['version']
                version_variables[f"{name}_version"] = version


    # Extract values from local_repo_config.yml
    repo_config = user_data['repo_config']
    cluster_os_type = user_data['cluster_os_type']
    cluster_os_version = user_data['cluster_os_version']
    repo_store_path = repo_config_data['repo_store_path']
    user_registries = repo_config_data['user_registry']

    # Load software configuration JSON files
    software_configs = load_software_config_json(software_names, cluster_os_type, cluster_os_version, user_json_path)
    
    for cluster_type, cluster_data in software_configs.items():
        for cluster_name, cluster_info in cluster_data.items():
            if 'cluster' in cluster_info and cluster_name in subgroup_names:
                print(f"Processing software stack: {cluster_type}")
                for package in cluster_info['cluster']:
                    process_package(package, repo_store_path, status_file_path, cluster_os_type,cluster_os_version, repo_config, version_variables, nerdctl_registry_host, user_registries, cluster_name, software_names)
                print()

    if cluster_os_type == 'rhel' or cluster_os_type == 'rocky':
        common_utility.run_createrepo_on_rhel_directories(repo_store_path, cluster_os_type, cluster_os_version, version_variables)
    if cluster_os_type == 'ubuntu':
        common_utility.run_createrepo_on_ubuntu_directories(repo_store_path, cluster_os_type, cluster_os_version, version_variables)

if __name__ == "__main__":
    main()
