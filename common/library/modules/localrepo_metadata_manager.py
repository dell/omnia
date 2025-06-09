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

# pylint: disable=import-error,no-name-in-module,line-too-long
#!/usr/bin/python

from pathlib import Path
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.process_metadata import (
    handle_generate_metadata,
    handle_compare_data,
    handle_update_data
)
from ansible.module_utils.local_repo.config import ( metadata_rerun_file_path )


"""
localrepo_metadata_manager.py

This Ansible custom module manages local repository metadata by:
- Generating metadata based on software and repository configuration files.
- Comparing and updating metadata while ignoring specific keys.
- Appending metadata footers with timestamps and policy info.

It supports check mode and can conditionally update metadata only if changes are detected.
"""

def main():
    
    argument_spec = {
        "software_config_path": {"type": "str", "required": True},
        "localrepo_config_path": {"type": "str", "required": True},
        "output_file": {"type": "str", "required": True},
        "update_metadata": {"type": "bool", "default": False},
        "ignore_keys": {"type": "list", "elements": "str", "default": ["lastrun_timestamp"]}
    }
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    sw_config = module.params["software_config_path"]
    repo_data = module.params["localrepo_config_path"]
    output_file = module.params["output_file"]
    ignore_keys = module.params['ignore_keys']
    update_flag = module.params["update_metadata"]

    try:
        if not output_file or not Path(output_file).exists():
            policy_result = handle_generate_metadata(sw_config,repo_data,output_file)
            module.exit_json(changed=True, policy=policy_result, msg="Metadata generated")
        else:
            if not update_flag:
                policy_result = handle_generate_metadata(
                    sw_config,
                    repo_data,
                    metadata_rerun_file_path
                )

                compare_output = handle_compare_data(
                    output_file,
                    metadata_rerun_file_path,
                    ignore_keys
                )
                same = compare_output.get('identical', False)
                module.exit_json(changed=not same, identical=same, msg="Compared metadata")
            else:
                update_result = handle_update_data(output_file,metadata_rerun_file_path,ignore_keys)
                module.exit_json(changed=update_result["changed"], diff=update_result["diff"])

    except Exception as e:
        module.fail_json(msg=str(e))

if __name__ == '__main__':
    main()
