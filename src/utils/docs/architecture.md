# Utils Domain -- Architecture

## System Context

```text
 collect_pxe.yml               +-------------------------------+   collected log bundle
 install_os_config.yml         |                               |   install_os_status.yml
 credentials ----------------->|          Utils Domain         |--> OIM log backup
 domain log directories        |                               |   utils_status.yml
 environment variables         +-------------------------------+
                                  |        |             |
                                  | SSH    | Redfish/NFS | local/NFS
                                  v        v             v
                               cluster   target node   backup store
                                nodes       iDRAC
```

PXE boot management is not part of this domain. Its playbook moved to the
orchestrator domain under `src/orchestrator/playbooks/setpxe/`.

## Execution Mode

Utils runs from the OIM. Most tasks use `localhost`; log collection connects by
SSH to configured cluster nodes, while OS deployment calls iDRAC Redfish APIs
and uses an NFS-hosted ISO. OIM log backup reads local domain directories and
can write to a local path or mounted NFS export.

---

## Public Tag Reference

Run commands from `src/utils` and select exactly one public tag:

```bash
ansible-playbook playbooks/utils.yml                         # setup + status only
ansible-playbook playbooks/utils.yml --tags precheck
ansible-playbook playbooks/utils.yml --tags setup
ansible-playbook playbooks/utils.yml --tags collect
ansible-playbook playbooks/utils.yml --tags install_os
ansible-playbook playbooks/utils.yml --tags backup_oim_logs
ansible-playbook playbooks/utils.yml --tags cleanup
ansible-playbook playbooks/utils.yml --tags cleanup_logs
ansible-playbook playbooks/utils.yml --tags cleanup_install_os
ansible-playbook playbooks/utils.yml --tags cleanup_backup_oim_logs
ansible-playbook playbooks/utils.yml --tags upgrade          # placeholder
ansible-playbook playbooks/utils.yml --tags rollback         # placeholder
```

### Tag Behavior Matrix

| Tag | Common setup | Utility action | Status written |
|-----|--------------|----------------|----------------|
| *(none)* / `setup` | Yes | None | Yes |
| `precheck` | Yes | Validate OIM environment | Yes |
| `collect` | Yes | Full remote log-collection flow | Yes |
| `install_os` | Yes | Full OS-install flow | Yes |
| `backup_oim_logs` | Yes | Full local/NFS backup flow | Yes |
| `cleanup` | Yes | Collected-log, OS-install, and OIM-log-backup cleanup | Yes |
| `cleanup_logs` | Yes | Collected-log retention cleanup | Yes |
| `cleanup_install_os` | Yes | OS-install temporary/credential cleanup | Yes |
| `cleanup_backup_oim_logs` | Yes | Remove all backup run directories | Yes |
| `upgrade` / `rollback` | Yes | Placeholder message only | Yes |

`cleanup_backup_oim_logs` selects only the OIM-log-backup cleanup; the combined
`cleanup` tag includes it with the other utility cleanup flows.

---

## Execution Flows

### Step 0: Common Setup (`tags: always`)

The `utils_setup` role optionally runs prerequisite, input-file, and disk-space
checks, then sets shared guard facts. These checks default to disabled because
each utility validates its own required inputs. The top-level play records a
start time and the final always-tagged play writes `utils_status.yml`.

### Precheck

The `precheck_environment` role:

- verifies that `/etc/omnia/omnia.env` exists;
- validates the exported hostname and domain against the OIM;
- verifies that `SYSTEM_ADMIN_NIC_IPV4` belongs to a local interface; and
- confirms that `OMNIA_DATA_PATH` exists.

### Cluster Log Collection

`collect.yml` uses the `log_collector` role in stages:

1. **setup** -- derive project paths and a shared timestamp;
2. **prepare** -- load `collect_pxe.yml`, create dynamic inventory groups, and
   create the local workspace;
3. **k8s** -- collect Kubernetes control-plane and worker logs;
4. **slurm** -- collect Slurm controller, compute, login, and login-compiler
   logs across configured architectures;
5. **bundle** -- add warning markers, optionally remove curated-support
   exclusions, create the tar.gz, compute SHA256, write metadata, and delete
   uncompressed workspace data.

Remote hosts are processed with `ignore_unreachable`. Missing source files,
collection errors, and unreachable nodes are represented in metadata; failed
or unreachable nodes also receive `SSH_COLLECTION_FAILED.txt` markers inside
the archive.

Direct play tags are `setup`, `prepare`, `k8s`, `slurm`, and `bundle`. The
public `collect` tag imports the complete flow.

### OS Installation

`install_os.yml` orchestrates these roles:

```text
validate_install_os_config
        |
collect_install_os_credentials
        |
     fetch_iso
        |
   iso_creation ---- generate_ks (alternative direct mode)
        |
   iso_delivery
        |
install_os_status.yml + utils_status.yml
```

The configuration validator applies requirements according to the direct tag:

- `credentials`: collect BMC and OS-root credentials only;
- `build_iso`: validate source ISO and NFS destination, then build a custom ISO;
- `deploy`: deploy an existing NFS-hosted ISO through iDRAC;
- `generate_ks`: render only `kickstart.ks` on the NFS share;
- no direct tag: credentials, build, deploy, and SSH verification end to end.

The custom ISO path must use `server:/path/file.iso` syntax. The roles support
embedded Kickstart or NFS Kickstart delivery and x86_64/aarch64 target values.

### OIM Domain Log Backup

`backup_oim_logs.yml` runs `oim_log_backup` in two stages:

1. **setup** -- load optional domain/path configuration, resolve destination,
   detect and mount a raw NFS export, and create the workspace;
2. **bundle** -- inspect each requested domain's `log/` directory, archive all
   present directories directly, compute SHA256, and write `metadata.json`.

The default domain set is `repo_manager`, `image_build_manager`, `orchestrator`,
`discovery`, `telemetry`, `build_stream`, and `utils`. Missing domain log
folders are skipped and listed as warnings; the run fails only when none of the
requested directories exists.

Destination precedence is CLI `backup_path`, config-file `backup_path`,
`OMNIA_BACKUP_PATH`, then the project-scoped default. Raw NFS exports are
mounted at `/tmp/omnia_backup_oim_logs_nfs`.

### Cleanup

| Flow | Behavior |
|------|----------|
| `cleanup_logs` | Selects tar.gz files older than `log_retention_days` (default 7), then removes every matching `omnia_logs_*` run directory and temporary `k8s`/`slurm` workspace; current run-directory deletion is not age-filtered |
| `cleanup_install_os` | Removes `/tmp/install_os`, unmounts/removes `/tmp/install_os_nfs`, and removes generated credentials by default; set `cleanup_credentials=false` to preserve them |
| `cleanup_backup_oim_logs` | Resolves the same local/NFS destination as backup and removes every `omnia_oim_logs_*` run directory; no retention policy |
| `cleanup` | Runs `cleanup_logs` and `cleanup_install_os`; it does not run OIM log-backup cleanup |

---

## Role Dependencies

```text
utils.yml
+-- utils_setup
+-- precheck_environment
+-- collect.yml
|   +-- log_collector
+-- install_os.yml
|   +-- validate_install_os_config
|   +-- collect_install_os_credentials
|   +-- fetch_iso
|   +-- iso_creation
|   +-- iso_delivery
+-- backup_oim_logs/backup_oim_logs.yml
|   +-- oim_log_backup
+-- cleanup/*.yml
+-- backup_oim_logs/cleanup_backup_oim_logs.yml
+-- utils_status_writer
```

The repository also contains reusable ARM, container-group, and Slurm
configuration roles. They are not imported by the current public `utils.yml`
flows.

---

## Runtime Layout

```text
$OMNIA_DATA_PATH/utils/
+-- input/<project>/
+-- output/<project>/
|   +-- collect/omnia_logs_<timestamp>/
|   +-- backup_oim_logs/omnia_oim_logs_<timestamp>/
|   +-- install_os_status.yml
|   +-- utils_status.yml
+-- log/<project>/
```

Ansible execution logs default to `/var/log/omnia/utils/utils.log`. The domain
initializer creates this directory, project runtime directories, installs
Python/Galaxy dependencies with checksum caching, and stages input templates.

---

## Key Design Decisions

1. **Utility flows are opt-in** -- an untagged top-level run performs setup and
   status writing, not every utility operation.
2. **Project-scoped contracts** -- inputs and outputs live below
   `$OMNIA_DATA_PATH/utils/{input,output}/<project>/`.
3. **No intermediate OIM backup copy** -- domain logs are streamed directly
   into the compressed archive.
4. **Partial log collection is useful** -- unreachable nodes and missing files
   become warnings while reachable nodes continue.
5. **Credentials are encrypted at rest** -- generated install credentials use
   Ansible Vault and a restrictive local key file.
6. **PXE ownership is external** -- PXE management belongs to orchestrator, not
   Utils.
