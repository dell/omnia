# cleanup

Runs the canonical Orchestrator cleanup engine for the components selected by
the calling cleanup playbook. Every selected component is attempted before the
role reports aggregate success or failure.

## What It Does

1. Loads and validates the resolved cleanup configuration.
2. Executes selected components in priority order.
3. Runs component pre-cleanup, cleanup, and post-cleanup task sets.
4. Records component results without hiding partial failures.
5. Reports a final summary and fails when any selected cleanup is incomplete.

Supported component definitions include Orchestrator artifacts, credentials,
Kubernetes, OpenCHAMI, OpenLDAP, Slurm, and storage mounts. Selection and
confirmation are owned by the calling cleanup playbook.

## Requirements

- Root privileges on the hosts owning the selected resources.
- Orchestrator paths and project context resolved by the cleanup preamble.
- Explicit confirmation for destructive component cleanup unless approval was
  intentionally skipped by supported automation.

## Role Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `cleanup_components` | Yes | Resolved component configuration selected for cleanup |
| `cleanup_execution_order` | Yes | Component names ordered by cleanup priority |
| `cleanup_credentials` | No | Include credential and vault-key removal; defaults to true in the full flow |

Internal paths and component constants are defined in `vars/main.yml` and
`config/default_cleanup.yml`.

## Dependencies

No role dependency is declared in `meta/main.yml`. Use the cleanup playbooks so
selection, validation, and confirmation occur before this role runs.

## Example

```bash
cd src/orchestrator/playbooks
ansible-playbook orchestrator.yml --tags cleanup \
  -e cleanup_credentials=false
```

For component-specific cleanup, use `cleanup/cleanup_orchestrator.yml` as
documented in `playbooks/cleanup/README.md`.

## License

Apache-2.0
