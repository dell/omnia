# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

# pylint: disable=import-error,no-name-in-module,too-many-locals,too-many-statements
#!/usr/bin/python

import os
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.standard_logger import setup_standard_logger
from ansible.module_utils.local_repo.software_utils  import (
    get_software_names_and_arch,
    check_csv_existence,
    get_failed_software,
    get_csv_file_path,
    get_csv_software,
    process_software,
    load_json,
    load_yaml,
    get_json_file_path,
    transform_package_dict,
    parse_repo_urls,
    set_version_variables,
    get_subgroup_dict,
    get_new_packages_not_in_status,
    remove_duplicates_from_trans,
    parse_additional_repos,
    validate_additional_repos_names
)

# Import configuration constants individually (excluding fresh_installation_status)
from ansible.module_utils.local_repo.config import (
    CSV_FILE_PATH_DEFAULT,
    USER_JSON_FILE_DEFAULT,
    LOG_DIR_DEFAULT,
    LOCAL_REPO_CONFIG_PATH_DEFAULT,
    SOFTWARE_CSV_FILENAME,
    ARCH_SUFFIXES
)

def main():
    """
    Prepares package lists and processes software based on user and repository configurations.

    This function initializes the module arguments and logger. It loads user data from a JSON file
    and repository configuration from a YAML file, retrieves cluster OS details, and determines the list
    of software. It then computes a boolean flag for fresh installation based on the CSV file's existence.
    For new software, the flag is enforced to True. The software is then processed, and the package tasks
    are aggregated and returned.
    """

    module_args = {
        "csv_file_path": {"type": "str", "required": False, "default": CSV_FILE_PATH_DEFAULT},
        "user_json_file": {"type": "str", "required": False, "default": USER_JSON_FILE_DEFAULT},
        "local_repo_config_path": {"type": "str", "required": False, "default": LOCAL_REPO_CONFIG_PATH_DEFAULT},
        "log_dir": {"type": "str", "required": False, "default": LOG_DIR_DEFAULT},
        "key_path": {"type": "str", "required": True},
        "sub_urls": {"type": "dict","required": False,"default": {}}

    }

    module = AnsibleModule(argument_spec=module_args)
    log_dir = module.params["log_dir"]
    user_json_file = module.params["user_json_file"]
    csv_file_path = module.params["csv_file_path"]
    local_repo_config_path = module.params["local_repo_config_path"]
    vault_key_path = module.params["key_path"]
    sub_urls =  module.params["sub_urls"]
    logger = setup_standard_logger(log_dir)
    start_time = datetime.now().strftime("%I:%M:%S %p")
    logger.info(f"Start execution time: {start_time}")

    try:
        user_data = load_json(user_json_file)
        cluster_os_type = user_data['cluster_os_type']
        cluster_os_version = user_data['cluster_os_version']
        repo_config = user_data['repo_config']

        final_tasks_dict = {}
        for arch in ARCH_SUFFIXES:
            software_csv_path = {}
            fresh_installation = {}
            software_list = {}
            csv_softwares = {}
            new_softwares = {}
            software_dict = {}
            json_path = {}
            status_csv_path = {}
            failed_softwares = []
            new_pkg_dict = {}
            tasks_dict = {}

            full_path = os.path.join(csv_file_path, arch, SOFTWARE_CSV_FILENAME)
            fresh_installation[arch] = True if not check_csv_existence(full_path) else False
            software_csv_path[arch] = full_path
            logger.info(f"sub rhel urls : {sub_urls}")
            logger.info(f"fresh_installation dict: {fresh_installation}")
            logger.info(f"software_csv_path: {software_csv_path}")
            software_list[arch] = get_software_names_and_arch(user_data,arch)
            logger.info(f"software_list: {software_list}")
            if not fresh_installation[arch]:
                csv_softwares[arch] = get_csv_software(software_csv_path[arch])
                new_softwares[arch] = [
                   software for software in software_list[arch] if software not in csv_softwares[arch]
                ]
            logger.info(f"Existing softwares in {arch} software csv: {csv_softwares}")
            logger.info(f"New software list for {arch}: {new_softwares}")
            # Build a dictionary mapping software names to subgroup data, if available
            subgroup_dict, software_names = get_subgroup_dict(user_data,logger)
            version_variables = set_version_variables(user_data, software_names, cluster_os_version,logger)

            logger.info("Preparing package lists...")
            for software in software_list[arch]:
                logger.info(f"Processing software: {software}")
                json_path[arch] = get_json_file_path(software, cluster_os_type,
                                                    cluster_os_version, user_json_file, arch)
                status_csv_path[arch] = get_csv_file_path(software, log_dir, arch)
                logger.info(f"json_path: {json_path}")
                logger.info(f"status_csv_path: {status_csv_path}")
                if not json_path[arch]:
                    logger.warning(f"Skipping {software}: JSON path does not exist.")
                    continue
                if not fresh_installation[arch]:
                    is_fresh_software = software in new_softwares.get(arch, [])
                else:
                    is_fresh_software = True
                logger.info(f"is_fresh_software: {is_fresh_software}")
                failed_softwares = get_failed_software(software_csv_path[arch])
                logger.info(f"failed softwares: {failed_softwares}")
                tasks, failed_packages = process_software(software, is_fresh_software, json_path[arch],
                                                           status_csv_path[arch],
                                                           subgroup_dict.get(software, None),logger)
                logger.info(f"tasks to be processed: {tasks}")
                logger.info(f"failed_packages : {failed_packages}")

                if not is_fresh_software:
                    pkgs = get_new_packages_not_in_status(json_path[arch],
                                                          status_csv_path[arch],
                                                          subgroup_dict.get(software, None),logger)

                    if pkgs:
                        logger.info(f"Additional software packages for {software}: {pkgs}")
                        tasks.extend(pkgs)

                if tasks:
                    tasks_dict[software] = tasks
                    trans=transform_package_dict(tasks_dict, arch,logger)
                    trans = remove_duplicates_from_trans(trans)
                    logger.info(f"Final tasklist to process: {trans}")
                    final_tasks_dict.update(trans)
        sw_archs = list(set(
            arch for sw in user_data.get("softwares", [])
            for arch in sw.get("arch", [])
        ))
        logger.info(f"Unique architectures from software_config: {sw_archs}")
        local_config, url_result = parse_repo_urls(repo_config, local_repo_config_path, version_variables, vault_key_path, sub_urls, logger, sw_archs)
        if not url_result:
            module.fail_json(f"{local_config} is either unreachable, invalid or has incorrect SSL certificates, please verify and provide correct details")

        # Validate additional_repos names for conflicts
        is_valid, error_msg = validate_additional_repos_names(local_repo_config_path, logger)
        if not is_valid:
            module.fail_json(msg=error_msg)

        # Parse additional_repos for aggregated repos feature
        additional_repos_config, error_msg = parse_additional_repos(
            local_repo_config_path, repo_config, vault_key_path, logger
        )
        if error_msg:
            module.fail_json(msg=error_msg)

        logger.info(f"Package processing completed: {final_tasks_dict}")
        module.exit_json(changed=False, software_dict=final_tasks_dict, local_config=local_config, additional_repos_config=additional_repos_config, sw_archs=sw_archs)

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        module.fail_json(msg=str(e))

if __name__ == "__main__":
    main()
