#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.common_functions import decrypt_certificate, encrypt_certificate

def run_module():
    """
    Runs the Ansible module for certificate encryption and decryption.

    This function takes in three parameters: action, cert_path, and vault_password_file.
    The 'action' parameter specifies whether to encrypt or decrypt the certificate.
    The 'cert_path' parameter is the path to the certificate file.
    The 'vault_password_file' parameter is the path to the vault password file.

    The function returns a dictionary containing the result of the operation.
    The dictionary includes the following keys:
    - changed: A boolean indicating whether the operation was successful.
    - message: A string describing the result of the operation.
    - status: An integer indicating the status of the operation.
    """
    module_args = {
        "action": {
            "type": "str",
            "required": True,
            "choices": ["encrypt", "decrypt"]
        },
        "cert_path": {
            "type": "str",
            "required": True
        },
        "vault_password_file": {
            "type": "str",
            "required": True,
            "no_log": True
        }
    }

    result = {
        "changed": False,
        "message": "",
        "status": 0
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

    action = module.params['action']
    cert_path = module.params['cert_path']
    vault_password_file = module.params['vault_password_file']

    if action == 'decrypt':
        status = decrypt_certificate(cert_path, vault_password_file)
        result['status'] = status
        result['message'] = "Certificate decrypted successfully." if status == 1 else "Decryption failed. Please check the path or vault key."

    elif action == 'encrypt':
        status = encrypt_certificate(cert_path, vault_password_file)
        result['status'] = status
        result['message'] = "Certificate encrypted successfully." if status == 1 else "Encryption failed. Please check the path or vault key."

    result['changed'] = (status == 1)
    if status == 0:
        module.fail_json(msg=result['message'], **result)

    module.exit_json(**result)

def main():
    """
    This is the main entry point of the module, responsible for calling the run_module function.
    It does not take any parameters and does not return any values.
    """
    run_module()

if __name__ == '__main__':
    main()
