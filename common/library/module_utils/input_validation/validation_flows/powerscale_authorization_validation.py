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

"""
PowerScale CSM Authorization validation module.
Contains validation logic for PowerScale multi-tenant storage authorization configuration.
"""

import csv
import json
import os
import yaml
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg
from ansible.module_utils.input_validation.common_utils.validation_utils import create_error_msg


def check_is_service_cluster_functional_groups_defined(
    errors, input_file_path, logger
):
    """
    Checks if service_kube_node_* and service_kube_control_plane_*
    are configured in the mapping file.

    Args:
        errors (list): A list to store error messages.
        input_file_path (str): The path to the input file.
        logger (object): Logger object.

    Returns:
        bool: True if service cluster functional groups are defined, False otherwise.
    """
    # Get the directory containing the input file
    input_dir = os.path.dirname(input_file_path)
    provision_config_path = os.path.join(input_dir, "provision_config.yml")

    # Check if provision_config.yml exists
    if not os.path.exists(provision_config_path):
        errors.append(
            create_error_msg(
                "provision_config.yml",
                provision_config_path,
                en_us_validation_msg.PROVISION_CONFIG_NOT_FOUND
            )
        )
        return False

    try:
        # Load provision_config.yml to get pxe_mapping_file_path
        with open(provision_config_path, 'r', encoding='utf-8') as f:
            provision_config = yaml.safe_load(f)

        pxe_mapping_file_path = provision_config.get('pxe_mapping_file_path', '')

        if not pxe_mapping_file_path or not os.path.exists(pxe_mapping_file_path):
            errors.append(
                create_error_msg(
                    "pxe_mapping_file_path",
                    pxe_mapping_file_path,
                    en_us_validation_msg.PXE_MAPPING_FILE_NOT_FOUND
                )
            )
            return False

        # Read the mapping file and check for service_kube_node functional groups
        with open(pxe_mapping_file_path, 'r', encoding='utf-8') as fh:
            raw_lines = fh.readlines()

        # Remove blank lines
        non_comment_lines = [ln for ln in raw_lines if ln.strip()]

        if not non_comment_lines:
            errors.append(
                create_error_msg(
                    "pxe_mapping_file_path",
                    pxe_mapping_file_path,
                    en_us_validation_msg.PXE_MAPPING_FILE_EMPTY_SERVICE_CLUSTER_MSG
                )
            )
            return False

        # Use csv.DictReader to parse the mapping file
        reader = csv.DictReader(non_comment_lines)

        # Check if all required service cluster functional groups are present
        # Required: service_kube_node_, service_kube_control_plane_
        has_kube_node = False
        has_control_plane = False

        for row in reader:
            functional_group = row.get('FUNCTIONAL_GROUP_NAME', '').strip()
            if functional_group.startswith('service_kube_node_'):
                has_kube_node = True
                logger.info(f"Service cluster functional group found: {functional_group}")
            elif functional_group.startswith('service_kube_control_plane_'):
                has_control_plane = True
                logger.info(f"Service cluster functional group found: {functional_group}")

        # Both must be present for a complete service cluster
        service_cluster_found = has_kube_node and has_control_plane

        if not service_cluster_found:
            missing = []
            if not has_kube_node:
                missing.append('service_kube_node_*')
            if not has_control_plane:
                missing.append('service_kube_control_plane_*')
            missing_groups = ', '.join(missing)
            logger.info(
                f"Service cluster incomplete. Missing functional groups: {missing_groups}"
            )

        return service_cluster_found

    except (yaml.YAMLError, IOError, csv.Error) as e:
        errors.append(
            create_error_msg(
                "pxe_mapping_file_path",
                pxe_mapping_file_path if 'pxe_mapping_file_path' in locals() else "unknown",
                f"Error reading mapping file: {str(e)}"
            )
        )
        return False


def validate_csm_auth_image_versions(csm_auth_values_path, config_paths, logger, errors):
    """
    Validates that CSM Authorization image versions in values.yaml match csi_driver_powerscale.json.

    Args:
        csm_auth_values_path (str): Path to the CSM Authorization values.yaml file.
        config_paths (dict): Dictionary containing resolved config file paths.
        logger (object): Logger object.
        errors (list): List to store error messages.
    """
    try:
        # Load CSM Authorization values.yaml
        with open(csm_auth_values_path, 'r', encoding='utf-8') as f:
            csm_auth_values = yaml.safe_load(f)

        # Extract image versions from values.yaml
        # Map of image names to their expected version
        csm_images = {}
        if 'authorization' in csm_auth_values and 'images' in csm_auth_values['authorization']:
            auth_images = csm_auth_values['authorization']['images']
            csm_images['csm-authorization-proxy'] = (
                auth_images.get('proxyService', {}).get('image', ''))
            csm_images['csm-authorization-tenant'] = (
                auth_images.get('tenantService', {}).get('image', ''))
            csm_images['csm-authorization-role'] = (
                auth_images.get('roleService', {}).get('image', ''))
            csm_images['csm-authorization-storage'] = (
                auth_images.get('storageService', {}).get('image', ''))
            csm_images['csm-authorization-controller'] = (
                auth_images.get('authorizationController', {}).get('image', ''))
            csm_images['opa'] = auth_images.get('opa', {}).get('image', '')
            csm_images['kube-mgmt'] = auth_images.get('opaKubeMgmt', {}).get('image', '')

        if 'redis' in csm_auth_values and 'images' in csm_auth_values['redis']:
            redis_images = csm_auth_values['redis']['images']
            csm_images['redis'] = redis_images.get('redis', {}).get('image', '')
            csm_images['redis-commander'] = redis_images.get('commander', {}).get('image', '')

        # Load csi_driver_powerscale.json from config_paths
        csi_json_path = config_paths.get("csi_driver_powerscale_json_path")

        if not csi_json_path or not os.path.exists(csi_json_path):
            logger.warning(en_us_validation_msg.POWERSCALE_AUTH_CSI_JSON_NOT_FOUND_MSG)
            return

        with open(csi_json_path, 'r', encoding='utf-8') as f:
            csi_config = json.load(f)

        # Extract image versions from csi_driver_powerscale.json
        csi_images = {}
        csi_ps_data = csi_config.get('csi_driver_powerscale', {})
        if csi_ps_data and 'cluster' in csi_ps_data:
            for item in csi_ps_data['cluster']:
                if item.get('type') == 'image':
                    package = item.get('package', '')
                    tag = item.get('tag', '')
                    # Store full image with tag
                    csi_images[package] = tag

        # Validate CSM Authorization images
        # Expected images to check (only CSM Authorization specific ones)
        _img_base = 'quay.io/dell/container-storage-modules'
        csm_auth_image_map = {
            f'{_img_base}/csm-authorization-proxy': 'csm-authorization-proxy',
            f'{_img_base}/csm-authorization-tenant': 'csm-authorization-tenant',
            f'{_img_base}/csm-authorization-role': 'csm-authorization-role',
            f'{_img_base}/csm-authorization-storage': 'csm-authorization-storage',
            f'{_img_base}/csm-authorization-controller': 'csm-authorization-controller',
            f'{_img_base}/csm-authorization-sidecar': 'csm-authorization-sidecar'
        }

        for image_path, csm_name in csm_auth_image_map.items():
            values_image = csm_images.get(csm_name, '')

            if values_image:
                # Extract version from values.yaml image
                values_version = values_image.split(':')[-1] if ':' in values_image else ''

                # Get version from csi_driver_powerscale.json
                csi_version = csi_images.get(image_path, '')

                if values_version and csi_version and values_version != csi_version:
                    errors.append(
                        create_error_msg(
                            f"CSM Authorization image version mismatch: {csm_name}",
                            (f"values.yaml: {values_version},"
                             f" csi_driver_powerscale.json: {csi_version}"),
                            en_us_validation_msg.powerscale_auth_image_version_mismatch_msg(
                                csm_name, values_version, csi_version
                            )
                        )
                    )

        logger.info("CSM Authorization image version validation completed")

    except (yaml.YAMLError, json.JSONDecodeError, IOError) as e:
        errors.append(
            create_error_msg(
                "csm_authorization_values_file_path",
                csm_auth_values_path,
                en_us_validation_msg.powerscale_auth_csm_values_validation_error_msg(str(e))
            )
        )


def validate_powerscale_authorization(
    kluster, softwares, input_file_path, config_paths, logger, errors
):
    """
    Validates PowerScale CSM Authorization configuration.

    Args:
        kluster (dict): Kubernetes cluster configuration from omnia_config.yml.
        softwares (list): List of software names from software_config.json.
        input_file_path (str): Path to omnia_config.yml.
        config_paths (dict): Dictionary containing resolved config file paths.
        logger (object): Logger object.
        errors (list): List to store error messages.
    """
    powerscale_auth = kluster.get("powerscale_authorization", {})
    if not powerscale_auth.get("enabled", False):
        return

    # Check if CSI driver is in software_config
    if "csi_driver_powerscale" not in softwares:
        errors.append(
            create_error_msg(
                "powerscale_authorization.enabled",
                "true",
                en_us_validation_msg.POWERSCALE_AUTH_CSI_DRIVER_MISSING_MSG
            )
        )

    # Check if service nodes are defined in PXE mapping
    service_cluster_defined = check_is_service_cluster_functional_groups_defined(
        errors, input_file_path, logger
    )
    if not service_cluster_defined:
        errors.append(
            create_error_msg(
                "powerscale_authorization.enabled",
                "true",
                en_us_validation_msg.POWERSCALE_AUTH_SERVICE_CLUSTER_MISSING_MSG
            )
        )

    # Validate csm_authorization_values_file_path (inside powerscale_authorization)
    csm_auth_values_path = powerscale_auth.get("csm_authorization_values_file_path")
    if not csm_auth_values_path or not csm_auth_values_path.strip():
        errors.append(
            create_error_msg(
                "powerscale_authorization.csm_authorization_values_file_path",
                csm_auth_values_path,
                en_us_validation_msg.POWERSCALE_AUTH_CSM_VALUES_PATH_REQUIRED_MSG
            )
        )
    elif not os.path.exists(csm_auth_values_path.strip()):
        errors.append(
            create_error_msg(
                "powerscale_authorization.csm_authorization_values_file_path",
                csm_auth_values_path,
                en_us_validation_msg.powerscale_auth_csm_values_not_found_msg(csm_auth_values_path)
            )
        )
    else:
        # Validate image versions match between values.yaml and csi_driver_powerscale.json
        validate_csm_auth_image_versions(csm_auth_values_path.strip(), config_paths, logger, errors)

    # Validate tenants and roles
    tenants = powerscale_auth.get("tenants") or []
    if not tenants:
        errors.append(
            create_error_msg(
                "powerscale_authorization.tenants",
                "[]",
                en_us_validation_msg.POWERSCALE_AUTH_TENANTS_REQUIRED_MSG
            )
        )
    else:
        for tenant in tenants:
            tenant_name = tenant.get("name", "")
            roles = tenant.get("roles") or []

            if not roles:
                errors.append(
                    create_error_msg(
                        f"powerscale_authorization.tenants[{tenant_name}].roles",
                        "[]",
                        en_us_validation_msg.powerscale_auth_tenant_roles_required_msg(tenant_name)
                    )
                )
            else:
                for role in roles:
                    storage_pool = role.get("storage_pool", "")
                    # Log warning about storage pool path requirement
                    if storage_pool:
                        logger.warning(
                            f"PowerScale Authorization: Storage pool path '{storage_pool}' "
                            f"for tenant '{tenant_name}', role '{role.get('name', '')}' "
                            "must already exist on the PowerScale cluster. "
                            "Omnia and CSI driver will NOT create this path automatically."
                        )
