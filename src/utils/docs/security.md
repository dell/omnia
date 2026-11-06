# Utils -- Security

## Credentials

- OS-install credentials are collected by the `install_os` flow and stored in `install_os_credentials.yml` with mode `0600`, Ansible Vault encrypted, with the vault key in `.install_os_credentials_key` in the same directory.
- `cleanup` and `cleanup_install_os` remove the credentials by default; `-e cleanup_credentials=false` keeps them.
- Credential values are validated with the shared security rules (`validate_credentials`, `security_filters`), and tasks that handle credentials use `no_log`.

## OS installation

- A user-provided Kickstart file without a `rootpw` directive, or without an `sshkey` directive, produces a warning: the installed system may have no root password, or the OIM SSH key will not be injected.
- The custom ISO is delivered through iDRAC virtual media; an NFS-delivered ISO requires the NFS directory to be mounted on the OIM.

## Log and configuration backups

OIM log backups archive each selected domain's `log/` directory with a `metadata.json` containing SHA256 checksums. Slurm configuration backups include `etc/slurm`, `etc/munge`, and `etc/my.cnf.d`, which contain the Munge key and database settings; rollback restores `slurmdbd.conf` and `munge.key` permissions. Treat backup destinations as sensitive and restrict access to them.
