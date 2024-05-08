import subprocess
import os
from jinja2 import Template
from common_utility import update_status

def process_deb_package(package, repo_store_path, status_file_path, cluster_os_type, cluster_os_version, repo_config, version_variables, cluster_name):
    """
    Process a Debian (deb) package
    Args:
        package: The package information dictionary.
        repo_store_path: Path to the repository store.
        status_file_path: Path to the status file.
        cluster_os_type: Cluster OS type.
        cluster_os_version: Cluster OS version.
        repo_config: Repository configuration.
        version_variables: Variables for rendering version template.
    """
    repo_name = package['repo_name']
    package_type = package['type']
    package_template = Template(package.get('package', None))  # Use Jinja2 Template for package
    # Render the packages, substituting Jinja variables if present
    package_name = package_template.render(**version_variables)
    print(f"Processing DEB: {package_name}, Repo Name: {repo_name}, Repo Config: {repo_config}")
    user_apt_conf_path= "/etc/apt/user_apt.conf"
    # Specify the repository names that should be skipped
    skip_repos = ['focal','jammy']

    omnia_always = ['amdgpu', 'cuda', 'ofed']
    
    # Construct the path based on the provided repository store format
    if cluster_name == 'beegfs':
        deb_directory = os.path.join(repo_store_path, 'cluster', 'apt', 'beegfs',
                version_variables.get('beegfs_version', ''))
    elif cluster_name == 'amdgpu':
        deb_directory = os.path.join(repo_store_path, 'cluster', 'apt', 'amdgpu',
                version_variables.get('amdgpu_version', ''))
    elif cluster_name == 'rocm':
        deb_directory = os.path.join(repo_store_path, 'cluster', 'apt', 'rocm',
                version_variables.get('rocm_version', ''))
    else:
        deb_directory = os.path.join(repo_store_path, 'cluster', cluster_os_type, cluster_os_version, 'deb')

    # Default status value
    status = "Skipped"

    # Check if the specified repo_name is in the list of repos to be skipped
    if repo_name not in skip_repos:
        try:
            # Different logic based on repo_config value
            if repo_config == 'always' or cluster_name in omnia_always:
                # Ensure directory exist
                os.makedirs(deb_directory, exist_ok=True)
                os.chdir(deb_directory)
                # Download the package
                command = ['apt-get' ,'download', package_name, '-o', f'Dir::Cache={deb_directory}']
                subprocess.run(command, check=True)
                print(f"DEB Package {package_name} downloaded successfully.")

                dependencies_cmd = ['apt-cache', 'depends', '--recurse', package_name]
                dependencies_output = subprocess.check_output(dependencies_cmd, text=True).splitlines()
                dependencies = []
                for line in dependencies_output:
                    parts = line.split()
                    if len(parts) > 1 and parts[0] == 'Depends:':
                        for part in parts[1:]:
                            if '<' in part or '>' in part:
                             break
                        else:
                            dependency = parts[1]
                            dependency = dependency.split(':')[0]
                            dependencies.append(dependency)

                # Download each dependency
                if repo_name != 'ldap':
                    for dependency in dependencies:
                        download_dependency_command = ['apt-get', 'download', dependency, '-o', f'Dir::Cache={deb_directory}']
                        try:
                            subprocess.run(download_dependency_command, check=True)
                            print(f"Package {dependency} downloaded successfully.")
                        except subprocess.CalledProcessError as e:
                            print(f"Error downloading package {dependency}: {e}")
                # Set status to "Success"
                status = "Success"

            elif repo_config == 'partial' and cluster_name not in omnia_always:
                try:
                    # Update user defined apt cache
                    subprocess.run(['apt-get', 'update', '-c', user_apt_conf_path], check=True)
                    subprocess.run(['apt-cache', 'show', package_name, '-c', user_apt_conf_path], check=True)
                    print(f"Package {package_name} is available in user repos. No need to download.")
                    status = "Skipped"
                except subprocess.CalledProcessError:
                    os.makedirs(deb_directory, exist_ok=True)
                    os.chdir(deb_directory)
                    # Download the package, update default cache
                    subprocess.run(['apt-get', 'update'], check=True)
                    command = ['apt-get' ,'download', package_name, '-o', f'Dir::Cache={deb_directory}']
                    subprocess.run(command, check=True)
                    print(f"DEB Package {package_name} downloaded successfully.")
                    status= "Success"

                dependencies_cmd = ['apt-cache', 'depends', '--recurse', package_name]
                dependencies_output = subprocess.check_output(dependencies_cmd, text=True).splitlines()
                dependencies = []
                for line in dependencies_output:
                    parts = line.split()
                    if len(parts) > 1 and parts[0] == 'Depends:':
                        for part in parts[1:]:
                            if '<' in part or '>' in part:
                             break
                        else:
                            dependency = parts[1]
                            dependency = dependency.split(':')[0]
                            dependencies.append(dependency)
                if repo_name != 'ldap':
                    for dependency in dependencies:
                        try:
                            subprocess.run(['apt-cache', 'show', dependency, '-c', user_apt_conf_path], check=True)
                            print(f"Dependency {dependency} is available in user repos. No need to download.")
                        except subprocess.CalledProcessError:
                            os.makedirs(deb_directory, exist_ok=True)
                            os.chdir(deb_directory)
                            command = ['apt-get' ,'download', dependency, '-o', f'Dir::Cache={deb_directory}']
                            subprocess.run(command, check=True)

            elif repo_config == 'never' and cluster_name not in omnia_always:
                status = "Skipped"
                print(f"DEB Package {package_name} wont be downloaded when repo_config is never")

        except subprocess.CalledProcessError:
            print(f"Error: Unable to process DEB Package {package_name}")
            status = "Failed"

    else:
        print(f"Skipping DEB {package_name} from repo {repo_name} based on repo_config: {repo_config}.")

    # Update status in your status file or perform further processing
    update_status(package_name, package_type, status, status_file_path)
