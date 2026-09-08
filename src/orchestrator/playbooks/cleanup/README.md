# Orchestrator Cleanup Framework

## Overview

Tag-based cleanup for Omnia orchestrator components. Every entry point delegates
selection, confirmation, execution, and reporting to the same cleanup role.

| Entry point | Purpose | Tags available |
|-------------|---------|----------------|
| `playbooks/orchestrator.yml` | Full cleanup of every component | `cleanup`, `cleanup_credentials` |
| `playbooks/cleanup/cleanup_orchestrator.yml` | Cleanup of individual components | `cleanup`, `cleanup_credentials`, plus one tag per component |
| `playbooks/cleanup/cleanup_openchami.yml` | Compatibility wrapper selecting OpenCHAMI | No tag required |
| `playbooks/cleanup/cleanup_openldap.yml` | Compatibility wrapper selecting OpenLDAP | No tag required |

Component-level tags are deliberately **not** accepted by `orchestrator.yml` — run
`cleanup_orchestrator.yml` directly when you need to clean a single component.

Cleanup never runs implicitly. `orchestrator.yml` invoked with no tags, or with any
non-cleanup tag such as `--tags execute`, performs no cleanup at all.

## Full cleanup (via orchestrator.yml)

Run from the `src/orchestrator` directory:

```bash
# All enabled components. Credential files are preserved.
ansible-playbook playbooks/orchestrator.yml --tags cleanup

# Credential files only.
ansible-playbook playbooks/orchestrator.yml --tags cleanup_credentials

# All enabled components AND credential files.
ansible-playbook playbooks/orchestrator.yml --tags cleanup,cleanup_credentials
```

`cleanup` cannot be combined with deployment tags (`prepare`, `deploy`, `provision`,
`execute`, `pxeboot`, `precheck`, `validate`, `upgrade`, `rollback`); doing so fails
with a tag-validation error.

## Component cleanup (via cleanup_orchestrator.yml)

```bash
# No tags: all enabled components, credentials preserved.
ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml

# A single component.
ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml --tags slurm

# Several components at once.
ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml --tags slurm,k8s
```

## Available tags

| Tag | Scope | Description |
|-----|-------|-------------|
| `cleanup` | both | All enabled components; credential files preserved |
| `cleanup_credentials` | both | Orchestrator credential files only (opt-in) |
| `slurm` | component playbook | Slurm NFS data and configuration |
| `k8s` | component playbook | K8s NFS data and configuration |
| `storage_mounts` | component playbook | Unmount orchestrator-deployed NFS mounts, clean fstab |
| `openchami` | component playbook | OpenCHAMI services, containers, and configuration |
| `openldap` | component playbook | OpenLDAP service, container, and data |
| `artifacts` | component playbook | Orchestrator deployment outputs and state files |

Slurm and Kubernetes cleanup remove their shared data first and then invoke
scoped `storage_mounts` cleanup. This ordering keeps the share reachable while
server-side data is deleted. Selecting `storage_mounts` directly cleans all
Orchestrator-managed mounts.

Component storage is resolved through the same contract used during
provisioning: `slurm_cluster[].nfs_storage_name`, optional
`slurm_cluster[].vast_storage_name`, and
`service_k8s_cluster[].nfs_storage_name` in `omnia_config.yml` must match
`mounts[].name` entries in `storage_config.yml`. Cleanup never invents a mount
name or fallback path. A missing, duplicate, or incomplete reference fails
before shared data is removed.

## Execution order

Components run in descending priority: OpenCHAMI 100, OpenLDAP 90, Slurm 80,
Kubernetes 70, storage mounts 60, artifacts 50, and credentials 10. Slurm and
Kubernetes perform their scoped unmount internally after deleting shared data;
the later storage-mount pass is idempotent.

## Shared (NFS) data cleanup

By default, Slurm and K8s cleanup removes their directories from the **shared
filesystem**, not just the local mount point — so the data is deleted on the NFS server.
This is done by writing through the mount point while the share is still mounted, which
means no SSH access to the NFS server is required and it works with NFS appliances.

Order of operations per component:

1. Remove the component's directories via the mount point (deletes them on the server)
2. Unmount the share and remove its `/etc/fstab` entry
3. Remove the now-empty local mount point directories

If the share is **not mounted** and the same path is not a local NFS export,
cleanup fails instead of claiming that requested server-side data was removed.
Mount or export the share and re-run the cleanup.

To keep shared data, set `cleanup_nfs_server: false` in the relevant component spec:

- `roles/cleanup/components/slurm/vars/component_spec.yml`
- `roles/cleanup/components/k8s/vars/component_spec.yml`

Directories listed under `preserve_directories` (Slurm: `slurm_backups`) are never
removed.

**Warning:** this is destructive and irreversible. On shared storage these paths
(`projects`, `scratch`, `apps`, …) may hold data Omnia did not create. Verify backups
before running, and do a `DRY_RUN=true` pass first.

## Confirmation

Cleanup asks for confirmation before deleting anything:

```
About to permanently delete data for: openchami, openldap, artifacts, storage_mounts, slurm, k8s
This includes data on shared NFS storage, which cannot be recovered.
Type 'yes' to proceed (anything else aborts)
```

Anything other than `yes` aborts before any component runs.

Non-interactive runs (CI, scripts, cron) receive no input and therefore **abort**. Pass
`SKIP_APPROVAL=true` to bypass the prompt:

```bash
SKIP_APPROVAL=true ansible-playbook playbooks/orchestrator.yml --tags cleanup
```

Confirmation is skipped automatically when `DRY_RUN=true`, since nothing is modified.

## Dry run mode

```bash
DRY_RUN=true ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml --tags slurm
```

Runs every component in Ansible check mode, so nothing is modified: services are not
stopped, containers are not removed, files are not deleted, and shares are not unmounted.
Tasks are still reported as `changed` to show what *would* happen — that report is the
point of the dry run. Post-cleanup state assertions are deferred until real execution,
because check mode intentionally leaves the current services and containers in place.

Applies to all components, including those reached indirectly (for example
`storage_mounts` when triggered by `slurm`).

## Failure handling

Already-absent services, containers, mounts, and files are treated as a
successful idempotent cleanup. Permission errors, malformed configuration,
failed removals, and unreachable shared data requested for deletion are real
failures.

The runner attempts every selected component and records a result for each.
Afterward it prints passed and failed component counts with actionable errors.
If any component failed, the playbook exits non-zero only after the summary has
been displayed.

OpenCHAMI cleanup explicitly stops the aggregate target and every generated
service unit, removes each deployed OpenCHAMI container, and verifies both
conditions before reporting success. It also removes the configured work and
log directories using the canonical `workdir` and `log_dir` component fields.

## Configuration

Component behaviour is defined in two places:

- `roles/cleanup/config/default_cleanup.yml` — which components exist, their priority,
  whether they are enabled, and the paths they remove.
- `roles/cleanup/components/<component>/vars/component_spec.yml` — per-component
  behaviour such as `cleanup_nfs_server` and directories to preserve.

## Troubleshooting

**"storage_config.yml not found"** — ensure `storage_config.yml` exists under
`$OMNIA_DATA_PATH/orchestrator/input/$OMNIA_PROJECT_NAME/`.

**"cannot safely resolve ... storage_name"** — ensure the storage name in
`omnia_config.yml` matches exactly one complete `mounts` entry in
`storage_config.yml`.

**"No components selected for cleanup"** — the supplied tag does not match any component.
Check the tag against the table above; component tags only work with
`cleanup_orchestrator.yml`.

**Tags appear to run but nothing happens** — confirm you are using the right entry point.
Component tags passed to `orchestrator.yml` are rejected by tag validation.

**Permission errors** — cleanup removes system paths and manages systemd units; run as
root or with sudo.
