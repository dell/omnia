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
# pylint: disable=import-error,no-name-in-module,too-many-positional-arguments,too-many-arguments,unused-argument
"""
Validates local repository configuration files for Omnia.
"""
import os
import glob
import re
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.local_repo.software_utils import load_yaml, load_json

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path


def check_subscription_status(logger=None):
    """
    Check if the system has an active Red Hat subscription.
    Subscription status is considered True if either entitlement
    certificates exist or the required Red Hat repository URLs are present.
    
    Checks mounted host paths (/etc/pki/entitlement, /etc/yum.repos.d/redhat.repo).

    Returns:
        bool: True if the system is subscribed (either entitlement certs
              exist or required repos are present), False otherwise.
    """    
    # 1. Check entitlement certs
    entitlement_certs = glob.glob(config.ENTITLEMENT_PEM)
    has_entitlement = len(entitlement_certs) > 0
    if logger:
        logger.info(f"Entitlement certs in {config.ENTITLEMENT_PEM}: {len(entitlement_certs)} found")

    # 2. Check redhat repos in redhat.repo
    repo_urls = []
    redhat_repo = config.REDHAT_REPO_FILE
    if os.path.exists(redhat_repo):
        with open(redhat_repo, "r") as f:
            for line in f:
                if line.startswith("baseurl ="):
                    url = line.split("=", 1)[1].strip()
                    if re.search(r"(codeready-builder|baseos|appstream)", url, re.IGNORECASE):
                        repo_urls.append(url)

    has_repos = len(repo_urls) > 0
    if logger:
        logger.info(f"Repo URLs in {redhat_repo}: {len(repo_urls)} found")

    # 3. Subscription status logic
    subscription_status = has_entitlement or has_repos
    if logger:
        logger.info(f"Subscription status: {subscription_status} (entitlement={has_entitlement}, repos={has_repos})")

    return subscription_status

# Below is a validation function for each file in the input folder
def validate_local_repo_config(input_file_path, data,
                               logger, module, omnia_base_dir,
                               module_utils_base, project_name):
    """
    Validates local repo configuration by checking cluster_os_type and
    omnia_repo_url_rhel fields are present and accessible.
    """
    errors = []
    base_repo_names = []
    local_repo_yml = create_file_path(input_file_path, file_names["local_repo_config"])
    
    user_registry = data.get("user_registry") 
    if user_registry:
        for registry in user_registry:
            host = registry.get("host")
            cert_path = registry.get("cert_path")
            key_path = registry.get("key_path")
            
            # Validate user_registry certificate and key paths
            if cert_path and not os.path.exists(cert_path):
                errors.append(create_error_msg(local_repo_yml, "user_registry", 
                                             f"Certificate file not found: {cert_path}"))
            
            if key_path and not os.path.exists(key_path):
                errors.append(create_error_msg(local_repo_yml, "user_registry", 
                                             f"Key file not found: {key_path}"))
    repo_names = {}
    sub_result = check_subscription_status(logger)
    logger.info(f"validate_local_repo_config: Subscription status: {sub_result}")
    all_archs = ['x86_64', 'aarch64']
    url_list = ["omnia_repo_url_rhel", "rhel_os_url", "user_repo_url"]
    for arch in all_archs:
        arch_repo_names = []
        arch_list = url_list + [url+'_'+arch for url in url_list]
         # define base repos dynamically for this arch if subscription registered 
        if sub_result:       
            base_repo_names = [f"{arch}_baseos",f"{arch}_appstream",f"{arch}_codeready-builder"]
            logger.info(f"Adding base repos for {arch}: {base_repo_names}")
        for repurl in arch_list:
            repos = data.get(repurl)
            if repos:
                arch_repo_names = arch_repo_names + [x.get('name') for x in repos]
        # Add additional_repos names for this arch
        additional_repos_key = f"additional_repos_{arch}"
        additional_repos = data.get(additional_repos_key)
        if additional_repos:
            arch_repo_names = arch_repo_names + [x.get('name') for x in additional_repos]
        repo_names[arch] = repo_names.get(arch, []) + arch_repo_names + base_repo_names
        logger.info(f"Total repos for {arch}: {repo_names[arch]}")

    for k,v in repo_names.items():
        if len(v) != len(set(v)):
            errors.append(create_error_msg(local_repo_yml, k, "Duplicate repo names found."))
            for c in set(v):
                if v.count(c) > 1:
                    errors.append(create_error_msg(local_repo_yml, k,
                                                f"Repo with name {c} found more than once."))

    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    software_config_json = load_json(software_config_file_path)

    # Extra validation: custom_slurm must have <arch>_slurm_custom in user_repo_url_<arch>
    for sw in software_config_json["softwares"]:
        if sw["name"] == "slurm_custom":
            for arch in sw.get("arch", []):
                expected_repo = f"{arch}_slurm_custom"

                # Look specifically under user_repo_url_<arch>
                user_repo_key = f"user_repo_url_{arch}"
                user_repos = data.get(user_repo_key, []) or []

                # Extract names safely
                user_repo_names = [r.get("name") for r in user_repos]

                if expected_repo not in user_repo_names:
                    errors.append(
                        create_error_msg(
                            local_repo_yml,
                            arch,
                            f"Missing required repo '{expected_repo}' in {user_repo_key} for slurm_custom.",
                        )
                    )

    os_ver_path = f"/{software_config_json['cluster_os_type']}/{software_config_json['cluster_os_version']}/"
    for software in software_config_json["softwares"]:
        sw = software["name"]
        arch_list = software.get("arch")
        for arch in arch_list:
            json_path = create_file_path(
            input_file_path,
            f"config/{arch}{os_ver_path}" + sw +".json")
            if not os.path.exists(json_path):
                errors.append(
                    create_error_msg(sw + '/' + arch, f"{sw} JSON file not found for architecture {arch}.", json_path))
            else:
                curr_json = load_json(json_path)
                pkg_list = curr_json[sw]['cluster']
                if sw in software_config_json:
                    for sub_pkg in software_config_json[sw]:
                        sub_sw = sub_pkg.get('name')
                        if sub_sw not in curr_json:
                            errors.append(
                                create_error_msg(sw + '/' + arch,
                                                json_path,
                                                f"Software {sub_sw} not found in {sw}."))
                        else:
                            pkg_list = pkg_list + curr_json[sub_sw]['cluster']
                for pkg in pkg_list:
                    if pkg.get("type") in ['rpm', 'rpm_list']:
                        repo_name = pkg.get("repo_name")
                        # Skip slurm_custom repo check (already validated above)
                        if sw == "slurm_custom" and repo_name.endswith("_slurm_custom"):
                            continue
                        # Skip base RHEL repo validation if subscription is enabled
                        if sub_result and repo_name in [f"{arch}_baseos", f"{arch}_appstream", f"{arch}_codeready-builder"]:
                            continue
                        if repo_name not in repo_names.get(arch, []):
                            errors.append(
                                create_error_msg(sw + '/' + arch,
                                                 f"Repo name {repo_name} not found.",
                                                json_path))
    return errors
