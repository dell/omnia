# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule

def convert_nic_to_ip(nic_ip_mapping):
    ip_to_nic_mapping = {}
    for nic, ips in nic_ip_mapping.items():
        for ip in ips:
            if ip in ip_to_nic_mapping:
                ip_to_nic_mapping[ip].append(nic)
            else:
                ip_to_nic_mapping[ip] = [nic]
    return ip_to_nic_mapping

def main():
    module = AnsibleModule(
        argument_spec=dict(
            nic_ip_mapping=dict(type="dict", required=True)
        )
    )

    nic_ip_mapping = module.params["nic_ip_mapping"]
    ip_to_nic_mapping = convert_nic_to_ip(nic_ip_mapping)

    module.exit_json(changed=False, ip_to_nic_mapping=ip_to_nic_mapping)

if __name__ == "__main__":
    main()
