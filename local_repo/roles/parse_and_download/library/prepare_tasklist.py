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
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.standard_logger import setup_standard_logger
from datetime import datetime
from ansible.module_utils.software_utils import (
    get_software_names,
    check_csv_existence,
    get_failed_software,
    process_software,
    load_json,
    load_yaml,
    get_json_file_path,
    get_csv_file_path,
    transform_package_dict,
    parse_repo_urls,
    set_version_variables,
    get_subgroup_dict
)
import logging
import json
import os
import re
 
def main():
    """
    The main function that prepares package lists and processes software.
 
    This function initializes the module arguments and sets up the logger.
    It loads the user data from a JSON file and the repository configuration
    data from a YAML file. It retrieves the cluster OS type and version, and
    the list of software names. It also sets up the version variables.
 
    The function then prepares the package lists and processes the software.
    For each software, it checks if it needs a fresh installation. If not,
    it skips the software. For each software, it retrieves the JSON and CSV
    file paths. It logs the software processing information and the subgroup
    data. It also checks if the software is in the list of failed software
    and skips it if necessary. It processes the software and stores the tasks
    in the software dictionary. Finally, it transforms the package dictionary
    and parses the repository URLs.
 
    Parameters:
    None
 
    Returns:
    None
 
    Raises:
    Exception: If an error occurs during the processing.
 
    """
    module_args = dict(
        csv_file_path=dict(type="str", required=False, default="/tmp/status_results_table.csv"),
        user_json_file=dict(type="str", required=False, default=""),
        local_repo_config_path=dict(type="str", required=False, default=""),
        log_dir=dict(type="str", required=False, default="/tmp/thread_logs"),
    )
 
    module = AnsibleModule(argument_spec=module_args)
 
    # versions = module.params['versions']
    log_dir = module.params["log_dir"]
    user_json_file = module.params['user_json_file']
    local_repo_config_path = module.params['local_repo_config_path']
    csv_file_path = module.params['csv_file_path']
 
    logger = setup_standard_logger(log_dir)
    start_time = datetime.now().strftime("%I:%M:%S %p")
    logger.info(f"Start execution time: {start_time}")
 
    try:
        user_data = load_json(user_json_file)
        repo_config_data = load_yaml(local_repo_config_path)
 
        cluster_os_type = user_data['cluster_os_type']
        cluster_os_version = user_data['cluster_os_version']
 
        software_list = get_software_names(user_json_file)
 
        # Build a dictionary of software_name -> subgroup_list if exists
       
        subgroup_dict , software_names = get_subgroup_dict(user_data)
 
        version_variables = set_version_variables(user_data, software_names, cluster_os_version)
        software_dict = {}
       
        logger.info("Preparing package lists...")
 
        for software in software_list:
            logger.info(f"Processing software: {software}")
            fresh_installation = 1 if not check_csv_existence(software, csv_file_path) else 0
 
            json_path = get_json_file_path(software, cluster_os_type, cluster_os_version, user_json_file)
            csv_path = get_csv_file_path(software, log_dir)
            logger.info(f"csv_path: {csv_path}")
           
            if not json_path:
                logger.warning(f"Skipping {software}: JSON path does not exist.")
                continue
               
 
            logger.info(f"{software}: JSON Path: {json_path}, CSV Path: {csv_path}, Fresh Install: {fresh_installation}")
            logger.info(f"Subgroup Data: {subgroup_dict.get(software, None)}")
            logger.info(f"Whole Subgroup Data: {subgroup_dict}")
 
            failed_softwares = get_failed_software(csv_file_path)
            if not fresh_installation and software not in failed_softwares:
                continue
            # Ensure we pass None for subgroup_list when not present
            logger.info(f"json_path: {json_path}")
            logger.info(f"csv_path: {csv_path}")
            tasks = process_software(software, fresh_installation, json_path, csv_path, subgroup_dict.get(software, None))
            logger.info(f"tasks: {tasks}")
           
            software_dict[software] = tasks
 
        software_dict=transform_package_dict(software_dict)
        local_config = parse_repo_urls(local_repo_config_path , version_variables)
 
        module.exit_json(changed=False, software_dict=software_dict  , local_config=local_config)
        logger.info(f"Package processing completed: {software_dict}")
 
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        module.fail_json(msg=str(e))
 
if __name__ == "__main__":
    main()
