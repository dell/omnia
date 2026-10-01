# Omnia Main Unit Tests

The local unit suite exercises `omnia-cli`, shared Bash completion, and
`omnia.sh` catalog management against temporary data paths. It does not run
playbooks or modify the installed Omnia environment.

## Execution

From `test/main/`:

```bash
python3 -m unittest discover -s ut -p 'test_*.py'
```

To run the catalog and completion cases only:

```bash
python3 -m unittest ut.test_omnia_cli.OmniaCliTest \
  -k catalog
python3 -m unittest ut.test_omnia_cli.OmniaCliTest \
  -k completion
```

## Coverage

The 37 cases in `test_omnia_cli.py` cover:

- domain input guidance, direct editing, and requirement labels;
- status/output contracts for all supported domains;
- log and nested-output handling, path overrides, and symlink confinement;
- command-aware completion for projects, domain tags, extra variables, and
  version-prefixed catalog selectors;
- recursive catalog discovery, exact selector activation, preservation during
  setup, and confirmed replacement with a timestamped backup.

The functional counterpart is `MAIN_FVT_CLI_V035`, documented in
`../fvt/README.md`; it runs `omnia.sh --list-catalogs` through the standard
Main validation framework and verifies discovery of the RHEL 10.0 and 10.2
catalog directories.
