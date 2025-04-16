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

#!/usr/bin/python

import os
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.standard_logger import setup_standard_logger
from ansible.module_utils.local_repo.software_utils  import (
    validate_repo_mappings,
    get_software_names,
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
    get_subgroup_dict
)

# Import configuration constants individually (excluding fresh_installation_status)
from ansible.module_utils.local_repo.config import (
    CSV_FILE_PATH_DEFAULT,
    USER_JSON_FILE_DEFAULT,
    LOCAL_REPO_CONFIG_PATH_DEFAULT,
    LOG_DIR_DEFAULT,
    SOFTWARE_CSV_FILENAME
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
    }

    module = AnsibleModule(argument_spec=module_args)
    log_dir = module.params["log_dir"]
    user_json_file = module.params["user_json_file"]
    local_repo_config_path = module.params["local_repo_config_path"]
    csv_file_path = module.params["csv_file_path"]

    logger = setup_standard_logger(log_dir)
    start_time = datetime.now().strftime("%I:%M:%S %p")
    logger.info(f"Start execution time: {start_time}")

    try:
        user_data = load_json(user_json_file)
        repo_config_data = load_yaml(local_repo_config_path)

        cluster_os_type = user_data['cluster_os_type']
        cluster_os_version = user_data['cluster_os_version']

        # Append the CSV filename from config (e.g. "software.csv")
        csv_file_path = os.path.join(csv_file_path, SOFTWARE_CSV_FILENAME)

        software_list = get_software_names(user_json_file)
        logger.info(f"software_list from software_config: {software_list}")

        # Compute fresh_installation as a boolean based on CSV file existence
        fresh_installation = True if not check_csv_existence(csv_file_path) else False
        logger.info(f"Fresh install: {fresh_installation}")

        csv_softwares = []
        if not fresh_installation:
            csv_softwares = get_csv_software(csv_file_path)
            logger.info(f"software from software.csv: {csv_softwares}")

        new_software = [software for software in software_list if software not in csv_softwares]
        logger.info(f"new software list: {new_software}")
        logger.info(f"Final software_list: {software_list}")

        # Build a dictionary mapping software names to subgroup data, if available
        subgroup_dict, software_names = get_subgroup_dict(user_data)
        version_variables = set_version_variables(user_data, software_names, cluster_os_version)
        software_dict = {}

        logger.info("Preparing package lists...")
        for software in software_list:
            logger.info(f"Processing software: {software}")
            logger.info(f"csv_file_path for software: {csv_file_path}")

            json_path = get_json_file_path(software, cluster_os_type, cluster_os_version, user_json_file)
            csv_path = get_csv_file_path(software, log_dir)
            logger.info(f"csv_path: {csv_path}")

            repo_validation_result = validate_repo_mappings(repo_config_data, json_path)
            if repo_validation_result:  # Only fail if errors exist
                logger.error(f"Repository validation failed: {repo_validation_result}")
                module.fail_json(msg="\n".join(repo_validation_result))
            else:
                logger.info("Repository validation passed successfully.")


            if not json_path:
                logger.warning(f"Skipping {software}: JSON path does not exist.")
                continue

            # If the software is new, enforce fresh installation
            if software in new_software:
                fresh_installation = True
            else:
                fresh_installation = False

            logger.info(f"{software}: JSON Path: {json_path}, CSV Path: {csv_path}, Fresh Install: {fresh_installation}")
            logger.info(f"Subgroup Data: {subgroup_dict.get(software, None)}")
            logger.info(f"Whole Subgroup Data: {subgroup_dict}")

            failed_softwares = get_failed_software(csv_file_path)
            logger.info(f"failed_softwares: {failed_softwares}")
            if not fresh_installation and software not in failed_softwares:
                continue

            logger.info(f"json_path: {json_path}")
            logger.info(f"csv_path: {csv_path}")
            tasks, failed_packages = process_software(software, fresh_installation, json_path, csv_path, subgroup_dict.get(software, None))
            logger.info(f"tasks: {tasks}")
            logger.info(f"failed_packages for software {software} are {failed_packages}")
            failed_packages = get_failed_software(csv_path)
            logger.info(f"failed_packages: {failed_packages}")

            software_dict[software] = tasks
 
        software_dict=transform_package_dict(software_dict)
        local_config, url_result = parse_repo_urls(local_repo_config_path , version_variables)
        if not url_result:
            module.fail_json(f"{local_config} is not reachable or invalid, please check and provide correct URL")
 
        module.exit_json(changed=False, software_dict=software_dict  , local_config=local_config)
        logger.info(f"Package processing completed: {software_dict}")

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        module.fail_json(msg=str(e))

if __name__ == "__main__":
    main()
