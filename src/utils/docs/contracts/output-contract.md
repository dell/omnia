# Utils Domain -- Output Contract

**Domain**: `utils` | **Collection**: `omnia.utils`

Outputs are project-scoped below
`<OMNIA_DATA_PATH>/utils/output/<project>/` unless an OIM backup destination is
overridden.

PXE boot outputs such as `failed_nodes.json` are not produced by Utils; PXE
management belongs to the orchestrator domain.

---

## 1. Collected Log Bundle

**Purpose**: Compressed logs gathered from configured Kubernetes, Slurm, login,
and login-compiler nodes.

**Location**:
`<OMNIA_DATA_PATH>/utils/output/<project>/collect/omnia_logs_<YYYYMMDD-HHMMSS>/`

**Producer**: `log_collector` bundle stage

```text
omnia_logs_<timestamp>/
+-- omnia_logs_<timestamp>.tar.gz
+-- metadata.json
```

The archive contains only available collected content under `k8s/` and
`slurm/`. Uncompressed workspaces are removed after the bundle is validated.
Failed or unreachable hosts receive an `SSH_COLLECTION_FAILED.txt` marker in
their node directory.

### metadata.json

| Field | Type | Description |
|-------|------|-------------|
| `bundle_name` | string | Archive filename |
| `tar_relative_path` | string | Archive-relative name recorded by the producer |
| `tar_sha256` | string | SHA256 checksum of the archive |
| `bundle_generated_at_utc` | string | UTC generation timestamp |
| `bundle_generated_at_local` | string | Local IST generation timestamp |
| `trigger_user` | string | OIM user that ran the playbook |
| `oim_host_os` | string | OIM OS description |
| `identifier` | string | Caller-provided identifier or hostname fallback |
| `collection_mode` | string | `complete logs` or `curated_support` |
| `exclusions_applied` | list[string] | Patterns removed in curated-support mode |
| `warning_count` | integer | Number of warnings |
| `warnings` | list[object] | Unreachable, missing-source, and collection-error details |

Curated-support mode removes files matching the role exclusion list before
archiving. Complete mode does not apply those exclusions.

---

## 2. OS Installation Outputs

### install_os_status.yml

**Location**:
`<OMNIA_DATA_PATH>/utils/output/<project>/install_os_status.yml`

**Producer**: Final status play in `install_os.yml` for build/deploy flows

| Field | Type | Description |
|-------|------|-------------|
| `utility` | string | Always `install_os` |
| `status` | string | `success` after successful SSH verification; otherwise `completed` |
| `timestamp` | string | Status generation time |
| `target_bmc_ip` | string | Configured iDRAC address |
| `target_admin_ip` | string | Configured installed-system address |
| `target_hostname` | string | Configured hostname |
| `custom_iso_path` | string | NFS URI of the custom ISO |
| `architecture` | string | Resolved `x86_64` or `aarch64` value |
| `kickstart_delivery_method` | string | `embedded` or `nfs` |
| `ssh_verified` | string | Lowercase `true` or `false` rendered by the playbook |

### NFS Artifacts

The directory containing `custom_iso_path` may contain:

| File | Description |
|------|-------------|
| Configured custom ISO filename | Repacked bootable ISO |
| `kickstart.ks` | Generated Kickstart file |
| `install_os_manifest.yml` | ISO-build manifest |

These files live on the user-selected NFS export rather than below the Utils
output directory.

---

## 3. OIM Domain Log Backup

**Default location**:
`<OMNIA_DATA_PATH>/utils/output/<project>/backup_oim_logs/omnia_oim_logs_<YYYYMMDD-HHMMSS>/`

The root can instead be a CLI-, config-, or environment-selected local path or
NFS export.

**Producer**: `oim_log_backup` bundle stage

```text
omnia_oim_logs_<timestamp>/
+-- omnia_oim_logs_<timestamp>.tar.gz
+-- metadata.json
```

Archive members retain domain-relative paths, for example
`repo_manager/log/...` and `utils/log/...`. Files matching the role's temporary
and backup-file exclusion patterns are omitted. Only the archive and metadata
remain; no uncompressed copy is created.

### metadata.json

| Field | Type | Description |
|-------|------|-------------|
| `backup_name` | string | Archive filename |
| `backup_generated_at_utc` | string | UTC generation timestamp |
| `backup_generated_at_local` | string | Local IST generation timestamp |
| `trigger_user` | string | OIM user that ran the backup |
| `oim_host_os` | string | OIM OS description |
| `domains_included` | list[string] | Requested domains whose log directory existed |
| `domains_skipped` | list[string] | Requested domains without a log directory |
| `archive_sha256` | string | SHA256 checksum of the archive |
| `backup_location` | string | Resolved local workspace/run directory |
| `exclusions_applied` | list[string] | Tar exclusion patterns |
| `warnings` | list[string] | Messages for skipped domains |

If every requested domain log directory is absent, the playbook fails and does
not produce a successful backup contract.

---

## 4. Utils Domain Status

**Location**: `<OMNIA_DATA_PATH>/utils/output/<project>/utils_status.yml`

**Producer**: `utils_status_writer`

**Consumer**: Omnia status/orchestration tooling

| Field | Type | Description |
|-------|------|-------------|
| `utility` | string | Always `utils` |
| `overall_status` | string | Status supplied by the calling playbook |
| `playbook` | string | Calling playbook name |
| `version` | string | Version currently emitted by the role |
| `started_at` | string | Execution start time |
| `completed_at` | string | Execution end time |
| `results` | list[object] | Optional per-role results |
| `errors` | list[string] | Optional execution errors |
| `warnings` | list[string] | Optional execution warnings |

The top-level `utils.yml` always writes this file. Imported utility playbooks
also write status for their own completion path.

---

## 5. Runtime and Ansible Logs

```text
<OMNIA_DATA_PATH>/utils/
+-- output/<project>/
|   +-- collect/
|   +-- backup_oim_logs/
|   +-- install_os_status.yml
|   +-- utils_status.yml
+-- log/<project>/

/var/log/omnia/utils/
+-- utils.log
```

The `log/<project>/` directory is the domain runtime-log location created by
`domain-init.sh`. The domain `ansible.cfg` writes top-level Ansible output to
`/var/log/omnia/utils/utils.log`; the standalone OIM backup playbook has its own
Ansible config and log filename.

---

## 6. Cleanup Effects

| Cleanup tag | Contract impact |
|-------------|-----------------|
| `cleanup_logs` | Finds archives older than `log_retention_days`, then removes all matching `omnia_logs_*` run directories; run-directory removal is not age-filtered |
| `cleanup_install_os` | Removes temporary local/NFS mounts and optionally generated credential files; it does not delete user-owned ISO artifacts on the NFS share |
| `cleanup_backup_oim_logs` | Deletes every `omnia_oim_logs_*` run directory from the resolved destination, including archives and metadata |
| `cleanup` | Runs collected-log and OS-install cleanup only |
