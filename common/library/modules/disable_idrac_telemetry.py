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

#!/usr/bin/python
"""Module to disable telemetry on iDRAC nodes via Redfish API.
This module connects to iDRAC nodes and disables telemetry collection
by sending PATCH requests to the Redfish API endpoint."""

import requests
import urllib3
from ansible.module_utils.basic import AnsibleModule

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def disable_telemetry_on_idrac(idrac_ip, username, password, timeout=30):
    """
    Disable telemetry on a single iDRAC node using Redfish API.

    Args:
        idrac_ip: IP address of the iDRAC
        username: iDRAC username
        password: iDRAC password
        timeout: Request timeout in seconds

    Returns:
        dict: Result containing success status and message
    """
    url = (
        f"https://{idrac_ip}/redfish/v1/Managers/"
        f"iDRAC.Embedded.1/Attributes"
    )

    # Try different telemetry property names in order of preference
    telemetry_properties = [
        "Telemetry.1.EnableTelemetry",
        "TelemetryService.1.EnableTelemetry", 
        "Telemetry.2.EnableTelemetry",
        "Redfish.1.TelemetryServiceEnabled"
    ]

    headers = {
        "Content-Type": "application/json"
    }

    for property_name in telemetry_properties:
        payload = {
            "Attributes": {
                property_name: "Disabled"
            }
        }

        try:
            response = requests.patch(
                url,
                json=payload,
                headers=headers,
                auth=(username, password),
                verify=False,
                timeout=timeout
            )
            
            if response.status_code in [200, 202, 204]:
                return {
                    "success": True,
                    "ip": idrac_ip,
                    "status_code": response.status_code,
                    "msg": f"Successfully disabled telemetry on iDRAC {idrac_ip} using {property_name}"
                }
            elif response.status_code == 400:
                # Property not supported, try next one
                continue
            else:
                return {
                    "success": False,
                    "ip": idrac_ip,
                    "status_code": response.status_code,
                    "msg": (
                        f"Failed to disable telemetry on iDRAC {idrac_ip}. "
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
                }
        
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "ip": idrac_ip,
                "msg": f"Timeout while connecting to iDRAC {idrac_ip}"
            }
        
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "ip": idrac_ip,
                "msg": f"Connection error while connecting to iDRAC {idrac_ip}"
            }
        
        except (requests.exceptions.RequestException, OSError) as e:
            return {
                "success": False,
                "ip": idrac_ip,
                "msg": f"Error disabling telemetry on iDRAC {idrac_ip}: {str(e)}"
            }

    # All properties failed
    return {
        "success": False,
        "ip": idrac_ip,
        "msg": (
            f"Failed to disable telemetry on iDRAC {idrac_ip}. "
            f"None of the supported telemetry properties were found: {', '.join(telemetry_properties)}"
        )
    }


def main():
    """Main function to execute the module logic."""
    module_args = {
        "idrac_ips": {"type": "list", "required": True, "elements": "str"},
        "username": {"type": "str", "required": True, "no_log": True},
        "password": {"type": "str", "required": True, "no_log": True},
        "timeout": {"type": "int", "default": 30},
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    idrac_ips = module.params["idrac_ips"]
    username = module.params["username"]
    password = module.params["password"]
    timeout = module.params["timeout"]

    disabled_ips = []
    failed_ips = []
    changed = False

    try:
        for idrac_ip in idrac_ips:
            result = disable_telemetry_on_idrac(
                idrac_ip=idrac_ip,
                username=username,
                password=password,
                timeout=timeout
            )

            if result.get("success"):
                disabled_ips.append(idrac_ip)
                changed = True
            else:
                failed_ips.append({
                    "ip": idrac_ip,
                    "msg": result.get("msg", "Unknown error")
                })

        module.exit_json(
            changed=changed,
            disabled_ips=disabled_ips,
            failed_ips=failed_ips,
            msg=f"Disabled telemetry on {len(disabled_ips)} iDRAC nodes."
        )

    except (requests.exceptions.RequestException, OSError) as e:
        module.fail_json(
            msg=f"An error occurred while disabling telemetry: {str(e)}",
            disabled_ips=disabled_ips,
            failed_ips=failed_ips
        )


if __name__ == "__main__":
    main()
