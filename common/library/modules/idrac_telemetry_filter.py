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

# pylint: disable=import-error

#!/usr/bin/python

import traceback
import requests
from requests.auth import HTTPBasicAuth
from requests import packages

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

packages.urllib3.disable_warnings()

def get_bmc_license_info(bmc_ip, username, password, module):
    """
	Queries the BMC for license information.

	Parameters:
	- bmc_ip (str): The BMC's IP address.
	- username (str): The BMC's username.
	- password (str): The BMC's password.
	- module (AnsibleModule): The Ansible module.

	Returns:
	- bool: True if the BMC has a valid Datacenter license, False otherwise.
	"""

    licenses_url = f"https://{bmc_ip}/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellLicenses"

    try:
        # Get the license details
        response = requests.get(
            licenses_url,
            verify=False,
            timeout=30,
            auth=HTTPBasicAuth(username, password))
        response.raise_for_status()

        # Extract the license data from the response
        license_data = response.json()

        for license_info in license_data.get("Members", []):
            # Initialize a dictionary to track conditions for this specific license
            conditions = {
                "iDRAC": False,
                "Data": False,
                "License": False,
                "Healthy": False
            }
            # Check LicenseDescription and LicensePrimaryStatus fields
            license_desc = license_info.get("LicenseDescription", [])
            license_primary_status = license_info.get("LicensePrimaryStatus", "")

            # Check for the required conditions in LicenseDescription
            if any("idrac" in desc.lower() for desc in license_desc):
                conditions["iDRAC"] = True
            if any("data" in desc.lower() for desc in license_desc):
                conditions["Data"] = True
            if any("license" in desc.lower() for desc in license_desc):
                conditions["License"] = True

            # Check if LicensePrimaryStatus is "Healthy"
            if "ok" in license_primary_status.lower():
                conditions["Healthy"] = True

            # Output the results based on the conditions
            if all(conditions.values()):
                return True
        module.warn(f"The system {bmc_ip} does not meet all the required license conditions.")
        return False

    except requests.exceptions.RequestException as err:
        module.warn(f"Error querying iDRAC licenses: {err}")
        return False


def get_bmc_firmware_info(bmc_ip, username, password, module, min_firmware_version_reqd):
    """
	Queries the BMC for firmware information.

	Parameters:
	- bmc_ip (str): The BMC's IP address.
	- username (str): The BMC's username.
	- password (str): The BMC's password.
	- module (AnsibleModule): The Ansible module.
	- min_firmware_version_reqd (int): The minimum required firmware version.

	Returns:
	- bool: True if the BMC's firmware version meets the minimum required version, False otherwise.
	"""

    manager_url = f"https://{bmc_ip}/redfish/v1/Managers/iDRAC.Embedded.1"

    try:
        # Get the iDRAC manager details
        response = requests.get(
            manager_url,
            verify=False,
            timeout=30,
            auth=HTTPBasicAuth(username, password))
        response.raise_for_status()

        # Extract the firmware version from the response
        manager_data = response.json()
        firmware_version = manager_data.get("FirmwareVersion", "Unknown")
        try:
            # Split the firmware version and convert to integer
            split_version = firmware_version.split('.')
            firmware_version_int = int(split_version[0])
        except (ValueError, IndexError) as e:
            module.warn(f"Error converting firmware version {firmware_version} to integer: {e}")
            firmware_version_int = 0

        if firmware_version_int >= min_firmware_version_reqd:
            return True

        module.warn(f"The system {bmc_ip} does not meet the minimum required firmware version.")
        return False

    except requests.exceptions.RequestException as err:
        module.warn(f"Error querying iDRAC manager: {err}")
        return False


def main():
    """
	Ansible module to filter BMCs based on their firmware version and license status.

	Parameters:
	- bmc_ip_list (list): List of BMC IPs to filter.
	- bmc_username (str): BMC username for authentication.
	- bmc_password (str): BMC password for authentication.
	- min_firmware_version_reqd (int): Minimum firmware version required for BMCs.

	Returns:
	- telemetry_idrac (list): List of BMC IPs that meet the requirements.
	- failed_idrac (list): List of BMC IPs that do not meet the requirements.
	- telemetry_idrac_count (int): Number of BMCs that meet the requirements.
	- failed_idrac_count (int): Number of BMCs that do not meet the requirements.
	"""

    # Define the module arguments
    module_args = {
        "bmc_ip_list": {"type": "list", "required": True},
        "bmc_username": {"type": "str", "required": True},
        "bmc_password": {"type": "str", "required": True, "no_log": True},
        "min_firmware_version_reqd": {"type": "int", "required": True}
    }

    # Create the Ansible module
    module = AnsibleModule(argument_spec=module_args)

    result = {
        "telemetry_idrac": [],
        "failed_idrac": [],
        "telemetry_idrac_count": 0,
        "failed_idrac_count": 0
    }

    bmc_ip_list = module.params['bmc_ip_list']
    bmc_username = module.params['bmc_username']
    bmc_password = module.params['bmc_password']
    min_firmware_version_reqd = module.params['min_firmware_version_reqd']

    try:

        for bmc_ip in bmc_ip_list:
            try:
                license_status = get_bmc_license_info(
                    bmc_ip, bmc_username, bmc_password, module
                )

                firmware_status = get_bmc_firmware_info(
                    bmc_ip, bmc_username, bmc_password, module, min_firmware_version_reqd
                )

                if license_status and firmware_status:
                    result["telemetry_idrac"].append(bmc_ip)
                    result["telemetry_idrac_count"] += 1
                else:
                    result["failed_idrac"].append(bmc_ip)
                    result["failed_idrac_count"] += 1

            except Exception:
                result["failed_idrac"].append(bmc_ip)
                result["failed_idrac_count"] += 1
                continue

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(
            msg=f"Unexpected failure: {to_native(e)}", exception=traceback.format_exc()
        )

if __name__ == '__main__':
    main()
