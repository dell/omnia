#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.validate_utils import validate_certificates

def main():
    """
    Ansible module to validate certificates for a repository.

    This module takes in the path to a local repository configuration file,
    the path to a directory containing certificates, and an optional key to
    specify which repository to validate. It then checks if the expected
    certificate files exist for the specified repository.

    :return: A dictionary with the result of the validation, including a
             boolean indicating whether the validation failed, and a message
             describing the result.
    """
    module_args = dict(
        local_repo_config_path=dict(type='str', required=True),
        certs_path=dict(type='str', required=True),
        repo_key=dict(type='str', required=False, default="user_repo_url")
    )

    result = dict(
        changed=False,
        failed=False,
        msg=""
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    try:
        validation_result = validate_certificates(
            local_repo_config_path=module.params['local_repo_config_path'],
            certs_path=module.params['certs_path'],
            repo_key=module.params['repo_key']
        )

        if validation_result.get("status") == "error":
            result["failed"] = True
            result["msg"] = "Certificate validation failed for the following repositories:\n"
            for item in validation_result.get("missing", []):
                repo_name = item.split(" ")[0]
                result["msg"] += (
                    f"  - {item}\n"
                    f"    Expected certificate files should exist under: "
                    f"{module.params['certs_path']}/{repo_name}/\n"
                )
        else:
            result["msg"] = f"All certificate checks passed for '{module.params['repo_key']}'."

    except Exception as e:
        module.fail_json(msg=f"Validation failed: {str(e)}", **result)

    module.exit_json(**result)

if __name__ == '__main__':
    main()
