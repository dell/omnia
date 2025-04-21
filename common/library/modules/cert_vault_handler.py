#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.local_repo.common_functions import is_encrypted, run_vault_command
import os

def process_file(file_path, vault_key, mode):
    if not os.path.isfile(file_path):
        return None, f"File not found: {file_path}"

    currently_encrypted = is_encrypted(file_path)

    if mode == 'encrypt':
        if currently_encrypted:
            return False, f"Already encrypted: {file_path}"
        else:
            code, out, err = run_vault_command('encrypt', file_path, vault_key)
            if code == 0:
                return True, f"Encrypted: {file_path}"
            else:
                return False, f"Failed to encrypt {file_path}: {err}"

    elif mode == 'decrypt':
        if not currently_encrypted:
            return False, f"Already decrypted: {file_path}"
        else:
            code, out, err = run_vault_command('decrypt', file_path, vault_key)
            if code == 0:
                return True, f"Decrypted: {file_path}"
            else:
                return False, f"Failed to decrypt {file_path}: {err}"

    return False, f"Invalid mode for {file_path}"

def main():
    module = AnsibleModule(
        argument_spec=dict(
            file_path=dict(type='str', required=False),
            dir_path=dict(type='str', required=False),
            vault_key=dict(type='str', required=True),
            mode=dict(type='str', required=True, choices=['encrypt', 'decrypt'])
        ),
        mutually_exclusive=[['file_path', 'dir_path']],
        required_one_of=[['file_path', 'dir_path']],
        supports_check_mode=False
    )

    file_path = module.params['file_path']
    dir_path = module.params['dir_path']
    vault_key = module.params['vault_key']
    mode = module.params['mode']

    if not os.path.isfile(vault_key):
        module.fail_json(msg=f"Vault key file not found: {vault_key}")

    messages = []
    changed = False

    if file_path:
        result, msg = process_file(file_path, vault_key, mode)
        if result is None:
            module.fail_json(msg=msg)
        changed = changed or result
        messages.append(msg)

    elif dir_path:
        if not os.path.isdir(dir_path):
            module.fail_json(msg=f"Directory not found: {dir_path}")

        files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
        if not files:
            module.exit_json(changed=False, msg="No files to process in the directory.")

        successes = 0
        for f in files:
            result, msg = process_file(f, vault_key, mode)
            messages.append(msg)
            if result:
                changed = True
                successes += 1

        if successes == 0:
            module.exit_json(changed=False, msg="No changes made. Files were already in desired state:\n" + "\n".join(messages))

    module.exit_json(changed=changed, msg="; ".join(messages))

if __name__ == '__main__':
    main()

