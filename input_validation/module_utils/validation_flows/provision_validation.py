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

import json
import validation_utils
import config
import en_us_validation_msg

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path

def validate_provision_config_credentials(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    provision_config_file_path = create_file_path(input_file_path, file_names["provision_config"])
    provision_config_json = validation_utils.load_yaml_as_json(provision_config_file_path, omnia_base_dir, project_name, logger, module)
    enable_switch_based = provision_config_json["enable_switch_based"]

    if enable_switch_based:
        switch_snmp3_username = data["switch_snmp3_username"]
        switch_snmp3_password = data["switch_snmp3_password"]
        if validation_utils.is_string_empty(switch_snmp3_username):
            errors.append(create_error_msg("switch_snmp3_username",switch_snmp3_username,en_us_validation_msg.switch_snmp3_username_empty_msg,))
        if validation_utils.is_string_empty(switch_snmp3_password):
            errors.append(create_error_msg("switch_snmp3_password", switch_snmp3_password, en_us_validation_msg.switch_snmp3_password_empty_msg))
        if not (validation_utils.validate_username(switch_snmp3_username, 4, 30)):
            errors.append(create_error_msg("switch_snmp3_username", switch_snmp3_username, en_us_validation_msg.switch_snmp3_username_fail_msg(4, 30)))
        if not (validation_utils.is_valid_password(switch_snmp3_password)):
            errors.append(create_error_msg("switch_snmp3_password", switch_snmp3_password, en_us_validation_msg.switch_snmp3_password_fail_msg))

    return errors

def validate_provision_config(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    software_config_json = json.load(open(software_config_file_path, "r"))
    cluster_os_type = software_config_json["cluster_os_type"]
    cluster_os_version = software_config_json["cluster_os_version"]

    pxe_mapping_file_path = data["pxe_mapping_file_path"]
    if not (validation_utils.verify_path(pxe_mapping_file_path)):
        errors.append(create_error_msg("pxe_mapping_file_path", pxe_mapping_file_path, en_us_validation_msg.pxe_mapping_file_path_fail_msg))

    iso_file_path = data["iso_file_path"]
    not_valid_iso_msg = validation_utils.verify_iso_file(iso_file_path, cluster_os_type, cluster_os_version)
    if not_valid_iso_msg:
        errors.append(create_error_msg("iso_file_path", iso_file_path, not_valid_iso_msg))

    timezone = data["timezone"]
    if not (validation_utils.validate_timezone(timezone, "module_utils/common/timezone.txt")):
        errors.append(create_error_msg("timezone", timezone, en_us_validation_msg.timezone_fail_msg))

    default_lease_time = data["default_lease_time"]
    if not (validation_utils.validate_default_lease_time(default_lease_time)):
        errors.append(create_error_msg("default_lease_time", default_lease_time, en_us_validation_msg.default_lease_time_fail_msg))

     # Validate NTP support
    ntp_support = data["ntp_support"]
    if ntp_support is None or ntp_support == "":
        errors.append(create_error_msg("ntp_support", ntp_support, en_us_validation_msg.ntp_support_empty_msg))
        
    return errors

def validate_network_spec(input_file_path, data, logger, module, omnia_base_dir, project_name):
    errors = []
    return errors