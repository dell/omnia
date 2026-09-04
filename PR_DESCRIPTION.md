# PR Description: Cleanup Framework Refactor

## Summary

Refactored the orchestrator cleanup framework to provide a clean, tag-based cleanup mechanism with proper safety guards. The cleanup is now opt-in only (no implicit execution), supports both full cleanup and component-level cleanup, and includes working dry-run and confirmation mechanisms.

## Key Changes

### New Entry Points

- **`cleanup_full.yml`** - Imported by `orchestrator.yml`, exposes only `cleanup` and `cleanup_credentials` tags
- **`cleanup_orchestrator.yml`** - Standalone playbook for component-level cleanup (`slurm`, `k8s`, `openchami`, `openldap`, `storage_mounts`, `artifacts`)
- **`tasks/prepare_and_select.yml`** - Shared cleanup logic (path resolution, config load, tag interpretation, component selection, ordering)

### Tag-Based Cleanup

**Via `orchestrator.yml`:**
- `--tags cleanup` - All enabled components (credentials preserved)
- `--tags cleanup_credentials` - Credential files only
- `--tags cleanup,cleanup_credentials` - All components + credentials

**Via `cleanup_orchestrator.yml` (direct):**
- No tags - All enabled components (credentials preserved)
- `--tags slurm` / `k8s` / `openchami` / `openldap` / `storage_mounts` / `artifacts` - Single component
- Component tags can be combined

Component-level tags are **not** accepted by `orchestrator.yml` (fail with "Unsupported tag") - this prevents accidental component cleanup through the main orchestrator flow.

### Safety Mechanisms

1. **Confirmation prompt** - Requires interactive `yes` before any cleanup. Non-interactive runs abort cleanly (no hang). Bypass with `SKIP_APPROVAL=true`.
2. **Dry-run mode** - `DRY_RUN=true` runs all components in check mode. Nothing is modified. Applies to all components including nested includes.
3. **Never-tag gating** - Cleanup never appears in orchestrator output unless explicitly tagged. No "skipping:" lines.
4. **Mount-aware NFS cleanup** - Deletes shared data via mount point when mounted, or directly from local export when this OIM is the NFS server. No SSH delegation required.

### NFS Server Cleanup

- Slurm and K8s cleanup now delete data on the NFS server by default (`cleanup_nfs_server: true`)
- No SSH required - deletes through the mount point (external server) or local export (OIM is server)
- Preserves `slurm_backups` directory
- Works with NFS appliances (no shell access required)

### Configuration Changes

- **`orchestrator_setup/vars/main.yml`**: Removed component tags (`slurm`, `k8s`, etc.) from `supported_tags` - they are only valid via `cleanup_orchestrator.yml`. Added invalid tag combinations for cleanup with other orchestrator tags.
- **`cleanup_openchami.yml` / `cleanup_openldap.yml`**: Removed `never` tags (now safe to run directly)
- **`component_spec.yml` files**: Default `cleanup_nfs_server: true` for Slurm and K8s

### Removed Code

- Duplicate `Cleanup credentials only` import in `orchestrator.yml`
- Debug tasks and duplicate banners
- SSH delegation for NFS server cleanup
- `cleanup_config.yml` (redundant - configuration moved to component_spec.yml)

## Breaking Changes

### 1. Cleanup is now interactive by default

**Before:** Cleanup ran without confirmation
**After:** Requires interactive `yes` prompt

**Migration:** For non-interactive use:
```bash
SKIP_APPROVAL=true ansible-playbook playbooks/orchestrator.yml --tags cleanup
```

### 2. Component tags rejected by orchestrator.yml

**Before:** `--tags slurm` on orchestrator.yml silently did nothing
**After:** Fails with "Unsupported tag 'slurm'"

**Migration:** Use the standalone playbook:
```bash
ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml --tags slurm
```

### 3. `cleanup_config.yml` removed

**Before:** User overrides in `cleanup_config.yml`
**After:** Override directly in `component_spec.yml`

**Migration:** Edit `roles/cleanup/components/<component>/vars/component_spec.yml` instead

## Testing

### Verification Commands

```bash
# Verify cleanup doesn't run without tags
ansible-playbook playbooks/orchestrator.yml

# Verify cleanup runs with correct tag
ansible-playbook playbooks/orchestrator.yml --tags cleanup

# Verify component-level cleanup
ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml --tags slurm

# Verify dry-run
DRY_RUN=true ansible-playbook playbooks/cleanup/cleanup_orchestrator.yml --tags slurm

# Verify component tags rejected by orchestrator
ansible-playbook playbooks/orchestrator.yml --tags slurm  # Should fail
```

### Tag Validation

Run the tag validation harness to verify all supported and invalid combinations work correctly.

## Known Issues

1. **External NFS server propagation** - Cannot verify on this system due to nested mount topology. Requires a host with clean mount topology to confirm that deleting through mount point reaches the external server.
2. **K8s config mismatch** - `storage_config.yml` declares k8s source as `172.16.107.121:/mnt/share/omnia_k8s` but actual mount is `172.16.0.254:/nfs-k8s`. Reconcile before running k8s cleanup.

## Files Added

- `playbooks/cleanup/cleanup_full.yml`
- `playbooks/cleanup/tasks/prepare_and_select.yml`

## Files Modified

- `playbooks/orchestrator.yml` - Import cleanup_full.yml only, tag validation
- `playbooks/cleanup/cleanup_orchestrator.yml` - Simplified to include shared tasks
- `playbooks/cleanup/README.md` - Updated documentation
- `playbooks/cleanup/cleanup_openchami.yml` - Removed never tag
- `playbooks/cleanup/cleanup_openldap.yml` - Removed never tag
- `roles/cleanup/components/slurm/tasks/cleanup.yml` - Mount-aware NFS cleanup, no SSH
- `roles/cleanup/components/k8s/tasks/cleanup.yml` - Mount-aware NFS cleanup, no SSH
- `roles/orchestrator_setup/vars/main.yml` - Tag validation updates

## Files Deleted

- `playbooks/cleanup/cleanup_config.yml` (redundant)
