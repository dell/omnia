# Utils -- Troubleshooting

Run `./omnia.sh --run utils --tags precheck` to validate the OIM hostname, domain, admin IP, data path, and setup state before using a utility.

## Common issues

| Symptom (message) | Cause | Action |
|-------------------|-------|--------|
| `Invalid tag usage detected` | Unsupported tag | Use a supported tag (one public tag at a time); see the README Tags section |
| `omnia.env is not installed system-wide` | Shared setup has not run | Run `sudo ./omnia.sh --setup-venv` |
| `Node inventory file not found: ... collect_pxe.yml` | Log collection input is missing | Create `collect_pxe.yml` with IP addresses under each functional group |
| `Invalid group name ... in collect_pxe.yml` | Group name is not `<role>_<arch>` with an optional OS/version segment | Use a valid role and architecture (`x86_64` or `aarch64`) |
| `User-provided Kickstart file not found` | `kickstart_file` path is wrong | Fix the path and re-run |
| `Failed to render Kickstart template` | A required template variable is unset in `install_os_config.yml` | Set the missing variables |
| `Failed to repack the ISO` | ISO creation failed | Check the Ansible log for the underlying error |
| `Cannot find local mount point for NFS server` | The NFS directory holding `custom_iso_path` is not mounted on the OIM | Mount the export locally, as shown in the message |
| `iDRAC at '<ip>' is not reachable` | BMC IP wrong or iDRAC/network down | Verify the BMC address, connectivity, and iDRAC status |
| `Custom ISO not found` in deploy mode | The ISO was not built | Run the `build_iso` stage first |
| `Target node ... is already reachable via SSH` | The node already has an OS | Set `force_reinstall: true` in `install_os_config.yml` to reinstall |
| `OS installation failed - target node ... did not become reachable via SSH` | Installation did not finish or the node has no network | Check the iDRAC virtual console; SEL warnings do not always indicate failure |
| Backup writes to an unexpected location | Backup path precedence | Order is `-e backup_path`, config `backup_path`, `OMNIA_BACKUP_PATH`, then the project default (Slurm utilities use `slurm_backup_path`) |

## Log locations

| Log | Location |
|-----|----------|
| Top-level playbook | `/var/log/omnia/utils/utils.log` |
| Domain runtime logs | `$OMNIA_DATA_PATH/utils/log/<project>/` |
| Last run status | `$OMNIA_DATA_PATH/utils/output/<project>/utils_status.yml` |
