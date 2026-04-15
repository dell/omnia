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
Validates csi  driver configuration files for Omnia.
"""
import os
import yaml
from pathlib import Path
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path
contains_software = validation_utils.contains_software
check_mandatory_fields = validation_utils.check_mandatory_fields
flatten_sub_groups = validation_utils.flatten_sub_groups


def validate_secret_isilon_clusters(data):
    """
    Validates csi secret file inputs for Omnia.
    """

    cluster_errors = []
    clusters = data.get("isilonClusters")

    # Check if isilonClusters is a defined, non-empty list
    if not isinstance(clusters, list) or len(clusters) == 0:
        cluster_errors.append("isilonClusters must be a non-empty list.")
        return cluster_errors  # Stop further checks

    for idx, item in enumerate(clusters):
        cluster_prefix = f"Cluster {idx + 1}"

        # Validate clusterName
        if not isinstance(item.get("clusterName"), str) or not item["clusterName"].strip():
            cluster_errors.append(f"{cluster_prefix}: Invalid or missing 'clusterName'.")

        # Validate username
        if not isinstance(item.get("username"), str) or not item["username"].strip():
            cluster_errors.append(f"{cluster_prefix}: Invalid or missing 'username'.")

        # Validate password
        if not isinstance(item.get("password"), str) or not item["password"].strip():
            cluster_errors.append(f"{cluster_prefix}: Invalid or missing 'password'.")

        # Validate endpoint
        if not isinstance(item.get("endpoint"), str) or not item["endpoint"].strip():
            cluster_errors.append(f"{cluster_prefix}: Invalid or missing 'endpoint'.")

        # Validate endpointPort if defined
        if "endpointPort" in item:
            if not isinstance(item["endpointPort"], int) or not 0 < item["endpointPort"] < 65536:
                cluster_errors.append(
                    f"{cluster_prefix}: 'endpointPort' must be an integer between 1 and 65535.")

        # Validate isDefault
        if "isDefault" not in item or not isinstance(item["isDefault"], bool):
            cluster_errors.append(
                f"{cluster_prefix}: 'isDefault' must be a boolean and must be defined.")

        # Validate skipCertificateValidation if defined
        if "skipCertificateValidation" in item:
            if item["skipCertificateValidation"] is not True:
                cluster_errors.append(
                    f"{cluster_prefix}: 'skipCertificateValidation' must be true if defined.")

        # Validate isiPath if defined
        if "isiPath" in item:
            isi_path = item["isiPath"]
            if (
                not isinstance(isi_path, str) or
                not isi_path.strip() or
                not isi_path.lstrip().startswith('/')
            ):
                cluster_errors.append(
                    f"{cluster_prefix}: 'isiPath' must be a non-empty valid Unix absolute path.")

        # Validate isiVolumePathPermissions if defined
        if "isiVolumePathPermissions" in item:
            perms = item["isiVolumePathPermissions"]
            if not isinstance(perms, str) or not perms.strip().isdigit():
                msg = (
                    f"{cluster_prefix}: 'endpointPort' must be an "
                    "integer between 1 and 65535."
                )
                cluster_errors.append(msg)
    return cluster_errors

def validate_value_file_inputs(values_data):
    """
    Validates csi value file inputs for Omnia.
    """

    value_errors = []

    def add_error(field_path, value, msg):
        value_errors.append(
            f"Validation Error - {field_path}: '{value}' -> {msg}"
        )

    # Helper to safely get nested values
    def get_nested(data, keys, default=None):
        for key in keys:
            if not isinstance(data, dict) or key not in data:
                return default
            data = data[key]
        return data

    # 1. controller.controllerCount == 1
    controller_count = get_nested(values_data, ["controller", "controllerCount"])
    if controller_count != 1:
        add_error("controller.controllerCount", controller_count, "Must be 1")

    # 2. controller.replication.enabled == false
    replication_enabled = get_nested(values_data, ["controller", "replication", "enabled"])
    if replication_enabled is None or replication_enabled is not False:
        add_error("controller.replication.enabled", replication_enabled, "Must be false")

    # 3. controller.resizer.enabled in [true, false]
    resizer_enabled = get_nested(values_data, ["controller", "resizer", "enabled"])
    if resizer_enabled not in [True, False]:
        add_error("controller.resizer.enabled", resizer_enabled, "Must be true or false")

    # 4. controller.snapshot.enabled == true
    snapshot_enabled = get_nested(values_data, ["controller", "snapshot", "enabled"])
    if snapshot_enabled is not True:
        add_error("controller.snapshot.enabled", snapshot_enabled, "Must be true")

    # 5. endpointPort is int in 1..65535
    endpoint_port = values_data.get("endpointPort")
    if endpoint_port is None or not isinstance(endpoint_port, int) or not 1 <= endpoint_port <= 65535:
        add_error("endpointPort", endpoint_port, "Must be between 1 and 65535")

    # 6. skipCertificateValidation == true
    skip_cert = values_data.get("skipCertificateValidation")
    if skip_cert is not True:
        add_error("skipCertificateValidation", skip_cert, "Must be true")

    # 7. isiAuthType in [0, 1]
    isi_auth = values_data.get("isiAuthType")
    if isi_auth not in [0, 1]:
        add_error("isiAuthType", isi_auth, "Must be 0 or 1")

    # 8. isiAccessZone is non-empty string
    isi_access = values_data.get("isiAccessZone")
    if not isi_access or not isinstance(isi_access, str) or not isi_access.strip():
        add_error("isiAccessZone", isi_access, "Must be a non-empty string")

    # 9. isiPath is Unix absolute path
    isi_path = values_data.get("isiPath")
    if not isinstance(isi_path, str) or not isi_path.startswith("/"):
        add_error("isiPath", isi_path, "Must be a valid Unix absolute path")

    # 10. isiVolumePathPermissions is a non-empty string
    permissions = values_data.get("isiVolumePathPermissions")
    if not permissions or not isinstance(permissions, str) or not permissions.strip():
        add_error("isiVolumePathPermissions", permissions, "Must be a valid octal string")

    return value_errors

def encrypt_file(secret_file_path, vault_secret_file_path):
    """
    encrypt the secret file
    """

    cmd = [
        "ansible-vault",
        "encrypt",
        secret_file_path,
        "--vault-password-file",
        vault_secret_file_path,
    ]
    return validation_utils.run_subprocess(cmd)

def decrypt_file(secret_file_path, vault_secret_file_path):
    """
    encrypt the secret file
    Takes 2 inputs: file name and secret file path
    """

    cmd = [
        "ansible-vault",
        "decrypt",
        secret_file_path,
        "--vault-password-file",
        vault_secret_file_path,
    ]
    return validation_utils.run_subprocess(cmd)

def process_encrypted_file(secret_file_path,vault_secret_file_path,errors):
    """
    Process the secret file
    decrypt the file first then parse it to get data
    """

    decrypted_file = decrypt_file(secret_file_path, vault_secret_file_path)
    if decrypted_file:
        try:
            content = Path(secret_file_path).read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            encrypt_file(secret_file_path, vault_secret_file_path)
            return data
        except FileNotFoundError:
            errors.append(create_error_msg("File not found",
                            secret_file_path, "Please check the associated file exists"))
        except yaml.YAMLError:
            errors.append(create_error_msg("Error loading yaml file",
                            secret_file_path, "Please check the associated file syntax"))
    else:
        errors.append(create_error_msg("Error occured when attempting to decrypt file.",
                            secret_file_path, "Please check that the assoicated vault file exists"))
    return decrypted_file

def validate_powerscale_secret_and_values_file(
    secret_file_path, values_file_path,
    errors, input_file_path):
    """
    Driver code to initiate the powerscale secret and values file input validation
    """

    #valiadte secret file inputs
    secrets_file_encrypted = validation_utils.is_file_encrypted(secret_file_path)
    file_path = os.path.dirname(input_file_path)
    vault_secret_file_path = os.path.join(file_path, ".csi_powerscale_secret_vault")

    if secrets_file_encrypted:
        secret_data = process_encrypted_file(secret_file_path, vault_secret_file_path,errors)
        if secret_data is None or secret_data is False:
            errors.append(create_error_msg(
                 "Secret File Load",
                    secret_file_path,
                   "Failed to load or parse secret.yaml file. It may be invalid or empty."
                ))
        else:
            secret_validation_errors = validate_secret_isilon_clusters(secret_data)
            if secret_validation_errors:
                for err in secret_validation_errors:
                    errors.append(
                        create_error_msg("Powerscale Secret File Validation Error:", err, None))

    #validate values file input
    with open(values_file_path, "r", encoding="utf-8") as f:
        values_data = yaml.safe_load(f)
    values_validation_errros = validate_value_file_inputs(values_data)
    if values_validation_errros:
        for value_err in values_validation_errros:
            errors.append(
                create_error_msg(f"Powerscale Value File Validation Error: ",value_err, None))
