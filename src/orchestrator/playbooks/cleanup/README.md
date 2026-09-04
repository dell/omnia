# Orchestrator Cleanup Framework

## Overview

Tag-based cleanup for Omnia orchestrator components. There are two entry points:

| Entry point | Purpose | Tags available |
|-------------|---------|----------------|
| `playbooks/orchestrator.yml` | Full cleanup of every component | `cleanup`, `cleanup_credentials` |
| `playbooks/cleanup/cleanup_orchestrator.yml` | Cleanup of individual components | `cleanup`, `cleanup_credentials`, plus one tag per component |

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

`--tags slurm` and `--tags k8s` automatically run `storage_mounts` first, so mounts are
released before the underlying directories are removed.

## Execution order

Components run in descending priority (OpenCHAMI 100, OpenLDAP 90, Slurm 80, K8s 70,
storage_mounts 60, artifacts 50, credentials 10), except that `storage_mounts` is always
reordered to run immediately before Slurm and K8s.

## Shared (NFS) data cleanup

By default, Slurm and K8s cleanup removes their directories from the **shared
filesystem**, not just the local mount point — so the data is deleted on the NFS server.
This is done by writing through the mount point while the share is still mounted, which
means no SSH access to the NFS server is required and it works with NFS appliances.

Order of operations per component:

1. Remove the component's directories via the mount point (deletes them on the server)
2. Unmount the share and remove its `/etc/fstab` entry
3. Remove the now-empty local mount point directories

If the share is **not mounted**, step 1 is skipped and a warning is printed — server-side
data is left untouched. Mount the share and re-run if you need it removed.

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
point of the dry run.

Applies to all components, including those reached indirectly (for example
`storage_mounts` when triggered by `slurm`).

## Configuration

Component behaviour is defined in two places:

- `roles/cleanup/config/default_cleanup.yml` — which components exist, their priority,
  whether they are enabled, and the paths they remove.
- `roles/cleanup/components/<component>/vars/component_spec.yml` — per-component
  behaviour such as `cleanup_nfs_server` and directories to preserve.

## Troubleshooting

**"storage_config.yml not found"** — ensure `storage_config.yml` exists in the
orchestrator input directory (`/opt/omnia/orchestrator/input/<project>/`).

**"No components selected for cleanup"** — the supplied tag does not match any component.
Check the tag against the table above; component tags only work with
`cleanup_orchestrator.yml`.

**Tags appear to run but nothing happens** — confirm you are using the right entry point.
Component tags passed to `orchestrator.yml` are rejected by tag validation.

**Permission errors** — cleanup removes system paths and manages systemd units; run as
root or with sudo.
