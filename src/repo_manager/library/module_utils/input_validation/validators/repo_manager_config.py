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
# pylint: disable=import-error,no-name-in-module,too-many-positional-arguments,too-many-arguments
# pylint: disable=too-many-locals,too-many-branches,too-many-statements
"""
Repo manager configuration validator.

This module validates repo_manager_config.yml for:
- User registry configuration
- Repository URL validation
- Subscription status checking
- JSON file existence for softwares
"""
import os
import glob
import re

from ansible.module_utils.input_validation.core.config import (
    files, SYSTEM_ENTITLEMENT_PATH, SYSTEM_REDHAT_REPO,
    CONTAINER_ENTITLEMENT_PATH, CONTAINER_REDHAT_REPO,
    OMNIA_ENTITLEMENT_PATH, OMNIA_REDHAT_REPO,
    ADDITIONAL_PACKAGES_SUPPORTED_SUBGROUPS
)
from ansible.module_utils.input_validation.core.utils import create_error_msg, create_file_path
from ansible.module_utils.input_validation.core.file_utils import load_json

from ansible.module_utils.local_repo.software_utils import get_json_file_path


def validate(
    input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name
):
    """
    Validates local repo configuration.

    Args:
        input_file_path (str): The path to the input file.
        data (dict): The data to be validated.
        logger: Logger instance.
        module: Ansible module instance.
        omnia_base_dir (str): The base directory of the Omnia configuration.
        module_utils_base (str): The base directory of the module utils.
        project_name (str): The name of the project.

    Returns:
        list: A list of errors encountered during validation.
    """
    errors = []
    repo_manager_config_yml = create_file_path(input_file_path, files["repo_manager_config"])

    # Validate user_registry
    user_registry = data.get("user_registry")
    if user_registry:
        for registry in user_registry:
            cert_path = registry.get("cert_path")
            key_path = registry.get("key_path")

            if cert_path and not os.path.exists(cert_path):
                errors.append(create_error_msg(
                    repo_manager_config_yml, "user_registry",
                    f"Certificate file not found: {cert_path}"))

            if key_path and not os.path.exists(key_path):
                errors.append(create_error_msg(
                    repo_manager_config_yml, "user_registry",
                    f"Key file not found: {key_path}"))

    # Validate user_repo_url entries have a 'name' field
    for repo_key in ("user_repo_url_x86_64", "user_repo_url_aarch64"):
        user_repos = data.get(repo_key)
        if user_repos:
            for repo in user_repos:
                repo_name = repo.get("name", "")
                if not repo_name:
                    errors.append(create_error_msg(
                        repo_manager_config_yml, repo_key,
                        "Each user repo entry must have a non-empty 'name' field."
                    ))

    # Collect repo names and check for duplicates
    repo_names = {}
    sub_result = _check_subscription_status(logger)
    logger.info(f"validate_repo_manager_config: Subscription status: {sub_result}")

    all_archs = ['x86_64', 'aarch64']
    url_list = ["omnia_repo_url_rhel", "rhel_os_url", "user_repo_url"]

    software_config_file_path = create_file_path(input_file_path, files["software_config"])
    software_config_json = load_json(software_config_file_path)
    cluster_os_type = software_config_json.get("cluster_os_type", "rhel")
    cluster_os_version = software_config_json.get("cluster_os_version", "10.0")

    for arch in all_archs:
        arch_repo_names = []
        arch_list = url_list + [url + '_' + arch for url in url_list]
        base_subscription_repos = []

        if sub_result:
            base_subscription_repos = ["baseos", "appstream", "codeready-builder"]
            logger.info(f"Base subscription repos for {arch}: {base_subscription_repos}")

        # Collect repo names from standard repo lists
        for repurl in arch_list:
            repos = data.get(repurl)
            if repos:
                for x in repos:
                    raw_name = x.get('name')
                    if raw_name:
                        arch_repo_names.append(raw_name)

        # Handle rhel_subscription_repo_config separately
        subscription_config_key = f"rhel_subscription_repo_config_{arch}"
        subscription_config = data.get(subscription_config_key, [])
        if subscription_config:
            for repo in subscription_config:
                raw_name = repo.get('name')
                if raw_name:
                    if raw_name not in base_subscription_repos:
                        arch_repo_names.append(raw_name)
                        logger.info(f"Adding new subscription config repo: {raw_name}")
                    else:
                        logger.info(f"Skipping base repo override from duplicate check: {raw_name}")

        # Add additional_repos names
        additional_repos_key = f"additional_repos_{arch}"
        additional_repos = data.get(additional_repos_key)
        if additional_repos:
            for x in additional_repos:
                raw_name = x.get('name')
                if raw_name:
                    arch_repo_names.append(raw_name)

        # Add base subscription repos
        if sub_result:
            arch_repo_names = arch_repo_names + base_subscription_repos

        repo_names[arch] = arch_repo_names
        logger.info(f"Total repos for {arch}: {repo_names[arch]}")

    # Check for duplicate repo names
    for k, v in repo_names.items():
        if len(v) != len(set(v)):
            errors.append(create_error_msg(repo_manager_config_yml, k, "Duplicate repo names found."))
            for c in set(v):
                if v.count(c) > 1:
                    errors.append(create_error_msg(
                        repo_manager_config_yml, k,
                        f"Repo with name {c} found more than once."))

    # Validate slurm_custom has slurm_custom in user_repo_url_<arch>
    for sw in software_config_json["softwares"]:
        if sw["name"] == "slurm_custom":
            for arch in sw.get("arch", []):
                expected_repo = "slurm_custom"
                user_repo_key = f"user_repo_url_{arch}"
                user_repos = data.get(user_repo_key, []) or []
                user_repo_names = [r.get("name") for r in user_repos]

                if expected_repo not in user_repo_names:
                    errors.append(
                        create_error_msg(
                            repo_manager_config_yml,
                            arch,
                            f"Missing required repo '{expected_repo}' in {user_repo_key} for slurm_custom.",
                        )
                    )

    # Validate JSON files for softwares
    supported_subgroups = ADDITIONAL_PACKAGES_SUPPORTED_SUBGROUPS
    additional_packages_warnings = False

    for software in software_config_json["softwares"]:
        sw = software["name"]
        arch_list = software.get("arch")
        software_version = software.get("version")

        for arch in arch_list:
            json_path = get_json_file_path(
                sw, cluster_os_type, cluster_os_version,
                software_config_file_path, arch,
                software_version=software_version
            )

            if not json_path or not os.path.exists(json_path):
                if sw == "service_k8s" and software_version:
                    expected_file = f"{sw}_v{software_version}.json"
                else:
                    expected_file = f"{sw}.json"
                errors.append(
                    create_error_msg(
                        sw + '/' + arch,
                        f"{sw} JSON file not found for architecture {arch}.",
                        expected_file
                    )
                )
            else:
                curr_json = load_json(json_path)
                pkg_list = curr_json[sw]['cluster']

                # Validate additional_packages subgroup keys
                if sw == "additional_packages":
                    if "additional_packages" not in curr_json:
                        logger.warning(
                            f"{sw}/{arch}: {json_path} - "
                            f"Required key 'additional_packages' is missing from the JSON file."
                        )
                        additional_packages_warnings = True

                    arch_supported = supported_subgroups.get(arch, [])
                    user_subgroups = [p.get('name') for p in software_config_json.get(sw, [])]

                    for json_key in curr_json:
                        if json_key == "additional_packages":
                            continue
                        if json_key not in arch_supported:
                            logger.warning(
                                f"{sw}/{arch}: {json_path} - "
                                f"Subgroup '{json_key}' is not supported for architecture {arch}."
                            )
                            additional_packages_warnings = True
                        elif json_key not in user_subgroups:
                            logger.warning(
                                f"{sw}/{arch}: {json_path} - "
                                f"Subgroup '{json_key}' is present in JSON but not listed "
                                f"under additional_packages in software_config.json."
                            )
                            additional_packages_warnings = True

                if sw in software_config_json:
                    for sub_pkg in software_config_json[sw]:
                        sub_sw = sub_pkg.get('name')
                        if sub_sw not in curr_json:
                            if sw == "additional_packages":
                                if sub_sw not in supported_subgroups.get(arch, []):
                                    continue
                                logger.warning(
                                    f"{sw}/{arch}: {json_path} - "
                                    f"Software {sub_sw} not found in {sw}."
                                )
                                additional_packages_warnings = True
                                continue
                            errors.append(
                                create_error_msg(
                                    sw + '/' + arch,
                                    json_path,
                                    f"Software {sub_sw} not found in {sw}."
                                )
                            )
                        else:
                            pkg_list = pkg_list + curr_json[sub_sw]['cluster']

                for pkg in pkg_list:
                    if pkg.get("type") in ['rpm', 'rpm_list']:
                        repo_name = pkg.get("repo_name")
                        if sw == "slurm_custom" and repo_name == "slurm_custom":
                            continue
                        if sub_result and repo_name in ["baseos", "appstream", "codeready-builder"]:
                            continue
                        if repo_name not in repo_names.get(arch, []):
                            errors.append(
                                create_error_msg(
                                    sw + '/' + arch,
                                    f"Repo name {repo_name} not found.",
                                    json_path
                                )
                            )

    if additional_packages_warnings:
        logger.info(
            "[INFO] Additional packages validation completed with warnings. "
            "Please review the log file for additional_packages configuration details."
        )

    return errors


def _check_subscription_status(logger=None):
    """
    Check if the system has an active Red Hat subscription enabled.

    Returns:
        bool: True if subscription is enabled, False otherwise.
    """
    # Check all possible entitlement certificate locations
    entitlement_paths = [
        (SYSTEM_ENTITLEMENT_PATH, SYSTEM_REDHAT_REPO),
        (CONTAINER_ENTITLEMENT_PATH, CONTAINER_REDHAT_REPO),
        (OMNIA_ENTITLEMENT_PATH, OMNIA_REDHAT_REPO),
    ]

    has_entitlement = False
    entitlement_certs = []
    repo_file_to_check = None

    for entitlement_path, repo_path in entitlement_paths:
        entitlement_certs = glob.glob(entitlement_path)
        has_entitlement = len(entitlement_certs) > 0
        if has_entitlement:
            repo_file_to_check = repo_path
            if logger:
                logger.info(
                    f"Found {len(entitlement_certs)} entitlement certs at {entitlement_path}"
                )
            break
    else:
        if logger:
            logger.info("No entitlement certs found in any known location")

    # Check repos
    has_repos = False
    repo_urls = []
    redhat_repo_used = None

    if repo_file_to_check and os.path.exists(repo_file_to_check):
        try:
            with open(repo_file_to_check, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("baseurl ="):
                        url = line.split("=", 1)[1].strip()
                        if re.search(r"(codeready-builder|baseos|appstream)", url, re.IGNORECASE):
                            repo_urls.append(url)

            if repo_urls:
                has_repos = True
                redhat_repo_used = repo_file_to_check
                if logger:
                    logger.info(f"Found {len(repo_urls)} repo URLs in {repo_file_to_check}")
            elif logger:
                logger.info(f"No required repo URLs found in {repo_file_to_check}")
        except (IOError, OSError) as e:
            if logger:
                logger.warning(f"Error reading {repo_file_to_check}: {e}")
    elif logger:
        logger.info(f"Repo file {repo_file_to_check} does not exist")

    subscription_enabled = has_entitlement and has_repos

    if logger:
        logger.info(
            f"Subscription enabled: {subscription_enabled} "
            f"(entitlement={has_entitlement}, repos={has_repos}, "
            f"entitlement_source={entitlement_certs[0] if entitlement_certs else 'None'}, "
            f"repo_source={redhat_repo_used})"
        )

    return subscription_enabled
