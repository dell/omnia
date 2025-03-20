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
import json

def load_rules(file_path):
    """Loads validation rules from JSON file."""
    with open(file_path, 'r') as file:
        return json.load(file)

def fetch_rule(field, rules):
    """Fetches validation rule for a given field."""
    if field not in rules:
        return (False, f"No validation rules found for '{field}'")

    rule = rules[field]
    return (True, rule.get("description", "No description available"))

def main():
    """Main function."""
    module_args = dict(
        credential_field=dict(type="str", required=True),
        rules_file=dict(type="str", required=False, default="../../input_validation/module_utils/schema/credential_rules.json")
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params

    # Load validation rules
    try:
        rules = load_rules(params["rules_file"])
    except Exception as e:
        module.fail_json(msg=f"Failed to load rules: {e}")

    # Fetch and return rule description
    success, message = fetch_rule(params["credential_field"], rules)
    if success:
        module.exit_json(changed=False, msg=message)
    else:
        module.fail_json(msg=message)

if __name__ == "__main__":
    main()
