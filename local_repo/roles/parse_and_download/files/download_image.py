# Copyright 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Module to handle downloading and processing image packages.
"""

import subprocess
from jinja2 import Template
from common_utility import update_status
import requests, shlex

json_headers = "application/vnd.oci.image.index.v1+json"

def process_image_tag_package(package_name, repo_config, nerdctl_registry_host, image_tag, crt_file_path):
    """
    Process an image package with tag.

    Args:
        package_name: The image name
        repo_config: Repository configuration.
        nerdctl_registry_host: Nerdctl registry host.
        image_tag: Tag value of image to be pulled.
    """
    print(f"Processing Image Package: {package_name}, Tag: {image_tag}")

    package_name = shlex.quote(package_name).strip("'\"")
    image_tag = shlex.quote(image_tag).strip("'\"")
    nerdctl_registry_host = shlex.quote(nerdctl_registry_host).strip("'\"")

    # Check if image exists in omnia_local_registry
    try:
        headers = {"Accept": json_headers}
        url = f"https://{nerdctl_registry_host}/v2/{package_name.split('/', 1)[-1]}/manifests/{image_tag}"
        response = requests.get(url, headers=headers, verify=crt_file_path)
        if response.status_code == 200:
            print(f"Image {package_name}:{image_tag} exists in the registry {nerdctl_registry_host}.")
            return "Success"
        else:
            pull_command = ["nerdctl", "pull", f"{package_name}:{image_tag}"]
            pull_command_all_platforms = ["nerdctl", "pull", f"{package_name}:{image_tag}", "--all-platforms"]
            tag_command = ["nerdctl", "tag", f"{package_name}:{image_tag}", f"{nerdctl_registry_host}/{package_name.split('/', 1)[-1]}:{image_tag}"]
            push_command = ["nerdctl", "push", f"{nerdctl_registry_host}/{package_name.split('/', 1)[-1]}:{image_tag}"]
            try:
                subprocess.run(pull_command, check=True)
                subprocess.run(tag_command, check=True)
                push_command_output = subprocess.run(push_command, capture_output=True, text=True)

                if push_command_output.returncode == 0:
                    return "Success"
                else:
                    if "failed to create a tmp single-platform image" in push_command_output.stderr:
                        subprocess.run(pull_command_all_platforms, check=True)
                        subprocess.run(tag_command, check=True)
                        subprocess.run(push_command, check=True)
                        return "Success"
                    else:
                        raise subprocess.CalledProcessError(returncode=1, cmd="failed to push image to private registry")
            except subprocess.CalledProcessError as e:
                return "Failed"
    except Exception as err:
        print(f"An error occurred: {err}")
        print(f"Exception occured while trying to access registry {nerdctl_registry_host}.")
        return "Failed"

def process_image_digest_package(package_name, repo_config, nerdctl_registry_host, image_digest, new_tag, crt_file_path):
    """
    Process an image package with digest.

    Args:
        package_name: The image name
        repo_config: Repository configuration.
        nerdctl_registry_host: Nerdctl registry host.
        image_digest: Digest value of image to be pulled.
        new_tag: New tag to be assigned to images with digest.
    """
    print(f"Processing Image Package: {package_name}, Digest: {image_digest}")
    # Check if image exists in omnia_local_registry

    nerdctl_registry_host = shlex.quote(nerdctl_registry_host).strip("'\"")
    package_name = shlex.quote(package_name).strip("'\"")
    new_tag = shlex.quote(new_tag).strip("'\"")
    image_digest = shlex.quote(image_digest).strip("'\"")


    try:
        headers = {"Accept": json_headers}
        url = f"https://{nerdctl_registry_host}/v2/{package_name.split('/', 1)[-1]}/manifests/{new_tag}"
        response = requests.get(url, headers=headers, verify=crt_file_path)
        if response.status_code == 200:
            print(f"Image {package_name}:{new_tag} exists in the registry {nerdctl_registry_host}.")
            return "Success"
        else:
            pull_command = ["nerdctl", "pull", f"{package_name}@sha256:{image_digest}"]
            pull_command_all_platforms = ["nerdctl", "pull", f"{package_name}@sha256:{image_digest}", "--all-platforms"]
            tag_command = ["nerdctl", "tag", f"{package_name}@sha256:{image_digest}", f"{nerdctl_registry_host}/{package_name.split('/', 1)[-1]}:{new_tag}"]
            push_command = ["nerdctl", "push", f"{nerdctl_registry_host}/{package_name.split('/', 1)[-1]}:{new_tag}"]
            try:
                subprocess.run(pull_command, check=True)
                subprocess.run(tag_command, check=True)
                push_command_output = subprocess.run(push_command, capture_output=True, text=True)
                if push_command_output.returncode == 0:
                    return "Success"
                else:
                    if "failed to create a tmp single-platform image" in push_command_output.stderr:
                        subprocess.run(pull_command_all_platforms, check=True)
                        subprocess.run(tag_command, check=True)
                        subprocess.run(push_command, check=True)
                        return "Success"
                    else:
                        raise subprocess.CalledProcessError(returncode=1, cmd="failed to push image to private registry")
            except subprocess.CalledProcessError as e:
                return "Failed"
    except Exception as err:
        print(f"An error occurred: {err}")
        print(f"Exception occured while trying to access registry {nerdctl_registry_host}.")
        return "Failed"

def check_image_in_registry(image_name, image_version, user_registries):
    """
    Check if an image exists in the user's registries.

    Args:
        image_name (str): The name of the image to check.
        image_version (str): The version of the image to check; can be tag/digest.
        user_registries (list): A list of dictionaries representing the user's registries.

    Returns:
        bool: True if the image exists in any of the user's registries, False otherwise.
    """
    image_name = shlex.quote(image_name).strip("'\"")
    image_version = shlex.quote(image_version).strip("'\"")

    if user_registries is not None and len(user_registries) > 0:
        for registry in user_registries:
            try:
                host = registry.get("host")
                cert_file_path = registry.get("cert_path").strip()
                cert_file_path = cert_file_path if cert_file_path else False

                print(f"Checking for image: {image_name}:{image_version} in registry {host}.")
                # Check if the image with the specified tag/digest exists
                headers = {"Accept": json_headers}
                url = f"https://{host}/v2/{image_name.split('/', 1)[-1]}/manifests/{image_version}"
                response = requests.get(url, headers=headers, verify=cert_file_path)
                if response.status_code == 200:
                    print(f"Image {image_name}:{image_version} exists in the registry {host}.")
                    return True
                else:
                    print(f"Image {image_name}:{image_version} not found in any user_registry.")
                    return False
            except Exception as err:
                print(f"An error occurred: {err}")
                print(f"Exception occured while trying to access registry {host}.")
                return False
    else:
        return False


def process_image_package(package, repo_config, nerdctl_registry_host, status_file_path, version_variables, user_registries, software_names, openssl_cert_path):
    """
    Process an image package.

    Args:
        package: The package information dictionary.
        repo_config: Repository configuration.
        nerdctl_registry_host: Nerdctl registry host.
        status_file_path: Path to the status file.
        version_variables: Variables for rendering version template.
    """

    package_name = package['package']
    package_type = package['type']

    # Define default values
    process_image_tag = False
    process_image_digest = False
    if len(software_names) and (software_names[-1] == "kserve" or software_names[-1] == "kubeflow"):
        new_tag= "omnia-" + software_names[-1]
    else:
        new_tag= "omnia"
    status= "Failed"
    complete_package_name = package_name

    if 'tag' in package:
        image_tag = package['tag']
        process_image_tag = True

    if 'digest' in package:
        image_digest = package['digest']
        process_image_digest = True

    if process_image_tag is True:
        # If software's version present in software_config.json, template to render value in tag
        tag_template = Template(package.get('tag', None))  # Use Jinja2 Template for version
        # Render the tag, substituting Jinja variables if present
        image_tag = tag_template.render(**version_variables)
        if repo_config == "always":
            status = process_image_tag_package(package_name, repo_config, nerdctl_registry_host, image_tag, openssl_cert_path)
        if repo_config == "partial":
            image_skip_status = check_image_in_registry(package_name, image_tag, user_registries)
            if not image_skip_status:
                status = process_image_tag_package(package_name, repo_config, nerdctl_registry_host, image_tag, openssl_cert_path)
            else:
                status = "Skipped"
        if repo_config == "never":
            status = "Skipped"
        complete_package_name = package_name + ":" + image_tag

    if process_image_digest is True:
        if repo_config == "always":
            status = process_image_digest_package(package_name, repo_config, nerdctl_registry_host, image_digest, new_tag, openssl_cert_path)
        if repo_config == "partial":
            image_skip_status = check_image_in_registry(package_name, "sha256:" + image_digest, user_registries)
            if not image_skip_status:
                status = process_image_digest_package(package_name, repo_config, nerdctl_registry_host, image_digest, new_tag, openssl_cert_path)
            else:
                status = "Skipped"
        if repo_config == "never":
            status = "Skipped"
        complete_package_name = package_name + "@sha256:" + image_digest

    # Update the status
    update_status(complete_package_name, package_type, status, status_file_path)