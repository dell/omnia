# log_collector

Collects predefined system logs from configured Kubernetes, Slurm, login, and
login-compiler nodes and produces a timestamped support bundle.

## Requirements

- SSH access from the OIM to target admin IPs
- `collect_pxe.yml` in the active Utils project input directory
- Sufficient OIM space below the project output directory

## Stages

| Stage | Purpose |
|-------|---------|
| `setup` | Resolve `$OMNIA_DATA_PATH`, project paths, and shared timestamp |
| `prepare` | Load `collect_pxe.yml`, build dynamic inventory, and create workspaces |
| `k8s_master` | Collect Kubernetes control-plane logs |
| `k8s_worker` | Collect Kubernetes worker logs |
| `slurm_ctl` | Collect Slurm controller logs |
| `slurm_node` | Collect Slurm compute logs for x86_64/aarch64 entries |
| `login_node` | Collect login-node logs |
| `login_compiler_node` | Collect login-compiler logs |
| `bundle` | Record warnings, archive content, compute SHA256, and remove uncompressed data |

`playbooks/collect.yml` maps these stages to the public direct tags `setup`,
`prepare`, `k8s`, `slurm`, and `bundle`. The top-level `utils.yml --tags collect`
imports the complete flow.

## Output

```text
$OMNIA_DATA_PATH/utils/output/$OMNIA_PROJECT_NAME/collect/
+-- omnia_logs_<timestamp>/
    +-- omnia_logs_<timestamp>.tar.gz
    +-- metadata.json
```

Unreachable nodes do not stop collection from remaining hosts. Metadata records
unreachable hosts, missing sources, and task errors; failed nodes receive an
`SSH_COLLECTION_FAILED.txt` marker in the archive.

The bundle task recognizes `curated_support` in `ansible_run_tags` and then
removes files matching `exclude_patterns` before archiving. This mode is an
internal bundle modifier rather than a standalone play tag.

## Key Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `collect_pxe_file` | Project input `collect_pxe.yml` | Node inventory |
| `log_root` | Project output `collect/` | Collection workspace and run output |
| `identifier` | Inventory hostname | Metadata identifier |
| `exclude_patterns` | Role-defined list | Files removed in curated-support mode |

## Dependencies

None.

## License

Apache License, Version 2.0
