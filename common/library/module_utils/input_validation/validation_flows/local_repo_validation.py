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
# pylint: disable=import-error,no-name-in-module,too-many-positional-arguments,too-many-arguments,unused-argument
"""
Validates local repository configuration files for Omnia.
"""
import os
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.local_repo.software_utils import load_yaml, load_json

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path

# Below is a validation function for each file in the input folder
def validate_local_repo_config(input_file_path, data,
                               logger, module, omnia_base_dir,
                               module_utils_base, project_name):
    """
    Validates local repo configuration by checking cluster_os_type and
    omnia_repo_url_rhel fields are present and accessible.
    """
    errors = []
    local_repo_yml = create_file_path(input_file_path, file_names["local_repo_config"])
    repo_names = {}
    base_repo_names = ['baseos', 'appstream']
    all_archs = ['x86_64', 'aarch64']
    url_list = ["omnia_repo_url_rhel", "rhel_os_url", "user_repo_url"]
    for arch in all_archs:
        arch_repo_names = []
        arch_list = url_list + [url+'_'+arch for url in url_list]

        for repurl in arch_list:
            repos = data.get(repurl)
            if repos:
                arch_repo_names = arch_repo_names + [x.get('name') for x in repos]
        repo_names[arch] = repo_names.get(arch, []) + arch_repo_names + base_repo_names

    for k,v in repo_names.items():
        if len(v) != len(set(v)):
            errors.append(create_error_msg(local_repo_yml, k, "Duplicate repo names found."))
            for c in set(v):
                if v.count(c) > 1:
                    errors.append(create_error_msg(local_repo_yml, k,
                                                f"Repo with name {c} found more than once."))

    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    software_config_json = load_json(software_config_file_path)

    roles_config_file_path = create_file_path(input_file_path, file_names["roles_config"])
    roles_config_dict = load_yaml(roles_config_file_path)
    def_archs = list({x["architecture"] for x in roles_config_dict["Groups"].values()})

    os_ver_path = f"/{software_config_json['cluster_os_type']}/{software_config_json['cluster_os_version']}/"
    for software in software_config_json["softwares"]:
        sw = software["name"]
        arch_list = software.get("arch", def_archs)
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
                        if pkg.get("repo_name") not in repo_names.get(arch, []):
                            errors.append(
                                create_error_msg(sw + '/' + arch,
                                                 f"Repo name {pkg.get('repo_name')} not found.",
                                                json_path))
    return errors
