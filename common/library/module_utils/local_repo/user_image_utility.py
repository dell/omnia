# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
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
# pylint: disable=import-error,no-name-in-module

import json
import requests
from requests.auth import HTTPBasicAuth
from jinja2 import Template
from ansible.module_utils.local_repo.standard_logger import setup_standard_logger
from ansible.module_utils.local_repo.parse_and_download import execute_command
from ansible.module_utils.local_repo.config import (
    pulp_container_commands
)
from ansible.module_utils.local_repo.container_repo_utils import (
    create_container_repository,
    sync_container_repository,
    extract_existing_tags,
    remote_creation_lock,
    repository_creation_lock
)

def check_image_in_registry(
    host,
    image,
    tag,
    cacert=None,
    key=None,
    username=None,
    password=None,
    logger=None,
):
    """
    Check if a container image exists in a user registry using Docker Registry HTTP API v2.

    Args:
        host (str): Registry hostname (without protocol)
        image (str): Image name
        tag (str): Image tag
        cacert (str, optional): Path to the CA certificate file for TLS authentication
        key (str, optional): Path to the client key file for TLS authentication
        username (str, optional): Registry username for basic authentication
        password (str, optional): Registry password for basic authentication
        logger (logging.Logger, optional): Logger instance for logging messages

    Returns:
        bool: True if image exists, False otherwise
    """

    if not host.startswith(("http://", "https://")):
        protocol = "https" if (cacert and key) else "http"
        host = f"{protocol}://{host}"
    image_url = f"{host}/v2/{image}/manifests/{tag}"
    logger.info(f"Checking image existence at: {image_url}")

    try:
        request_args = {
            "timeout": 10,
            "verify": False,
            "headers": {
                "Accept": (
                    "application/vnd.oci.image.manifest.v1+json,"
                    "application/vnd.oci.image.index.v1+json,"
                    "application/vnd.docker.distribution.manifest.v2+json,"
                    "application/vnd.docker.distribution.manifest.list.v2+json"
                )
            },
        }

        if cacert and key:
            request_args["cert"] = (cacert, key)

        response = requests.get(image_url, **request_args)

        if response.status_code == 200:
            logger.info(f"Image '{image}:{tag}' exists in registry '{host}'")
            return True

        if response.status_code == 404:
            logger.info(
                f"Image '{image}:{tag}' does not exist in registry '{host}'"
            )
            return False

        logger.error(
            f"Unexpected HTTP {response.status_code} while checking image "
            f"'{image}:{tag}' in registry '{host}'"
        )

    except requests.exceptions.SSLError as e:
        logger.error(
            f"TLS error while connecting to registry '{host}': {e}"
        )
    except requests.RequestException as e:
        logger.exception(f"Network error while checking image: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error while checking image: {e}")

    return False

def create_user_remote_container(
    remote_name,
    base_url,
    package_content,
    policy_type,
    cacert,
    key,
    logger,
    tag_val=None,
):
    """
    Creates or updates a container remote in Pulp using either digest or tag logic.

    Args:
        remote_name (str): Name of the container remote.
        base_url (str): Base URL of the remote registry.
        package_content (str): Identifier for the container package.
        policy_type (str): Remote policy (e.g., 'immediate', 'on_demand').
        cacert (str): Path to the CA certificate for TLS authentication.
        key (str): Path to the client key for TLS authentication.
        logger (logging.Logger): Logger for recording actions and errors.
        tag_val (str, optional): Optional tag to include in the remote configuration.

    Returns:
        bool or dict: True on success, False on failure, or a dict with command result.
    """
    try:
        if tag_val is None:
            remote_exists = execute_command(
                pulp_container_commands["show_container_remote"] % remote_name, logger
            )
            if not remote_exists:
                if cacert and key:
                    ca_cert = f"@{cacert}"
                    client_key = f"@{key}"
                    command = pulp_container_commands["create_user_remote_digest"] % (
                        remote_name,
                        base_url,
                        package_content,
                        policy_type,
                        ca_cert,
                        client_key,
                    )
                else:
                    command = pulp_container_commands["create_container_remote_for_digest"] % (
                        remote_name,
                        base_url,
                        package_content,
                        policy_type,
                    )
                result = execute_command(command, logger)
                logger.info(f"Remote created successfully: {remote_name}")
                return result

            logger.info(f"Remote {remote_name} already exists.")
            if cacert and key:
                ca_cert = f"@{cacert}"
                client_key = f"@{key}"
                command = pulp_container_commands["update_user_remote_digest"] % (
                    remote_name,
                    base_url,
                    package_content,
                    policy_type,
                    ca_cert,
                    client_key,
                )
            else:
                command = pulp_container_commands["update_remote_for_digest"] % (
                    remote_name,
                    base_url,
                    package_content,
                    policy_type,
                )
            result = execute_command(command, logger)
            logger.info(f"Remote updated successfully: {remote_name}")
            return result

        # tag_val is provided
        remote_exists = execute_command(
            pulp_container_commands["show_container_remote"] % remote_name, logger
        )

        if not remote_exists:
            if cacert and key:
                ca_cert = f"@{cacert}"
                client_key = f"@{key}"
                command = pulp_container_commands["create_user_remote_tag"] % (
                    remote_name,
                    base_url,
                    package_content,
                    policy_type,
                    tag_val,
                    ca_cert,
                    client_key,
                )
            else:
                command = pulp_container_commands["create_container_remote"] % (
                    remote_name,
                    base_url,
                    package_content,
                    policy_type,
                    tag_val,
                )
            result = execute_command(command, logger)
            if result:
                logger.info(f"Remote '{remote_name}' created successfully.")
                return True

            logger.error(f"Failed to create remote '{remote_name}'.")
            return False

        logger.info(f"Remote '{remote_name}' already exists. Updating include_tags.")
        existing_tags = extract_existing_tags(remote_name, logger)

        if tag_val in existing_tags:
            logger.info(
                f"Tag '{tag_val}' already exists for remote '{remote_name}'. No update needed."
            )
            return True

        new_tags = existing_tags + [tag_val]
        tags_json = json.dumps(new_tags)

        if cacert and key:
            ca_cert = f"@{cacert}"
            client_key = f"@{key}"
            update_command = pulp_container_commands["update_user_remote_tag"] % (
                remote_name,
                base_url,
                package_content,
                policy_type,
                tags_json,
                ca_cert,
                client_key,
            )
        else:
            update_command = pulp_container_commands["update_container_remote"] % (
                remote_name,
                base_url,
                package_content,
                policy_type,
                tags_json,
            )
        result = execute_command(update_command, logger)

        if result:
            logger.info(f"Remote '{remote_name}' updated successfully with tags: {new_tags}")
            return True

        logger.error(f"Failed to update remote '{remote_name}'.")
        return False

    except Exception as e:
        logger.error(f"Failed to create remote {remote_name}. Error: {e}")
        return False


def process_user_registry(
    package,
    host,
    package_content,
    version_variables,
    cacert,
    key,
    logger,
):
    """
    Sets up and syncs a user container image repository using a tag or digest.

    Args:
        package (dict): Package metadata with 'package', and either 'tag' or 'digest'.
        host (str): Registry host URL.
        package_content (str): Image name to process.
        version_variables (dict): Variables to render the tag if templated.
        logger (Logger): Logger for debug and error output.

    Returns:
        tuple: (bool success, str image_identifier)
    """
    logger.info("#" * 30 + f" {process_user_registry.__name__} start " + "#" * 30)

    user_reg_prefix = "container_repo_"
    repository_name = (
        f"{user_reg_prefix}{package['package'].replace('/', '_').replace(':', '_')}"
    )
    remote_name = f"user_remote_{package['package'].replace('/', '_').replace(':', '_')}"
    package_identifier = package["package"]
    policy_type = "immediate"
    if not host.startswith(("http://", "https://")):
        protocol = "https" if (cacert and key) else "http"
        host = f"{protocol}://{host}"
    base_url = f"{host}/"

    logger.info("Creating user container repository")
    with repository_creation_lock:
        result = create_container_repository(repository_name, logger)

    if result is False or (isinstance(result, dict) and result.get("returncode", 1) != 0):
        return False, package_identifier

    logger.info("Creating user registry remote")

    if "digest" in package:
        package_identifier += f":{package['digest']}"
        result = create_user_remote_container(
            remote_name, base_url, package_content, policy_type, cacert, key, logger
        )
        if result is False or (isinstance(result, dict) and result.get("returncode", 1) != 0):
            return False, package_identifier

    elif "tag" in package:
        tag_val = package["tag"]
        if "{{" in tag_val and "}}" in tag_val:
            try:
                template = Template(tag_val)
                tag_val = template.render(**version_variables)
            except Exception as exc:
                logger.error(f"Failed to render tag template: {exc}")
                return False, package_identifier

        with remote_creation_lock:
            result = create_user_remote_container(
                remote_name, base_url, package_content, policy_type, cacert, key, logger, tag_val
            )
        if not result:
            return False, package_identifier
    
    sync_result = sync_container_repository(repository_name, remote_name, package_content, logger)

    if sync_result is False or (isinstance(sync_result, dict) and sync_result.get("returncode", 1) != 0):
        return False, package_identifier

    return True, package_identifier

def handle_user_image_registry(package, package_content, version_variables, user_registries, logger):
    """
    Checks user-defined container registries for the presence of a
    specific image (by tag or digest) and processes it if found.

    Parameters:
        package (dict): Dictionary containing package metadata.
        package_content (str): Image name or content identifier.
        version_variables (dict): Variables used to render the tag template.
        user_registries (list): List of user registries with required authentication and TLS information.
        logger (logging.Logger): Logger object for logging messages.

    Returns:
        tuple: (True, package content) if image is found and successfully processed; False otherwise.
    """
    logger.info("#" * 30 + f" {handle_user_image_registry.__name__} start " + "#" * 30)
    result = False
    package_info = None
    image_name = package_content
    tag_val = None

    try:
        # Determine tag or digest for the image
        if "tag" in package:
            tag_template = Template(package["tag"])
            tag_val = tag_template.render(**version_variables)
        elif "digest" in package:
            digest_hash = package["digest"]
            tag_val = f"sha256:{digest_hash}"

        for registry in user_registries:
            host = registry.get("host")
            cacert = registry.get("cert_path")
            key = registry.get("key_path")
            # username = registry.get("username")
            # password = registry.get("password")

            logger.info(f"Checking image {image_name}:{tag_val} in registry {host}")
            image_found = check_image_in_registry(
                host=host,
                image=image_name,
                tag=tag_val,
                cacert=cacert,
                key=key,
                username=None,
                password=None,
                logger=logger
            )

            if image_found:
                logger.info(f"Image '{image_name}:{tag_val}' found in registry '{host}'")
                result, package_info = process_user_registry(package, host, package_content, version_variables, cacert, key, logger)
                break
            else:
                logger.info(f"Image '{image_name}:{tag_val}' not found in registry '{host}', checking next registry...")
        else:
            logger.info(f"Image '{image_name}:{tag_val}' not found in any user registry")
            result = False

    except Exception as e:
        logger.error(f"Exception in {handle_user_image_registry.__name__}: {e}")
        result = False

    logger.info("#" * 30 + f" {handle_user_image_registry.__name__} end " + "#" * 30)
    return result, package_info

