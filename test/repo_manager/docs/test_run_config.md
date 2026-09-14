# Test Run Configuration

`test_run_config.yml` controls Repo Manager batch execution. Entries run in
YAML order when `./run_validation.sh --config` is used.

## Command contract

| Command | FVT behavior |
|---------|--------------|
| `exec` | Run only `deploy`-marked playbook-trigger tests |
| `verify` | Run only non-deploy verification tests |
| `test` | Run `exec`, then `verify`; stop before verification if execution fails |

Unit tests use `test`; the shared runner treats `exec` and `verify` as aliases
for the same deterministic UT suite.

## Scenario fields

```yaml
fvt_repo_manager:
  prepare:
    run: false
    command: "test"
    suite: ""
    marker: "sanity"
```

- `run` must be an unquoted YAML boolean.
- `command` must be `exec`, `verify`, or `test`.
- `suite` is an immediate subdirectory below the selected FVT tag.
- `marker` is one marker, an AND expression using `+`, or an OR expression
  using `,`.

## Repo Manager lifecycle

An untagged `fvt_repo_manager test` executes these deploy stages in order:

1. `precheck`
2. `prepare`
3. `execute`
4. `status`

It then verifies the non-destructive scenarios. `cleanup`, `cleanup_repos`,
`negative`, and `catalog` are excluded from aggregate discovery; co-located
tests marked `negative` or `destructive` are filtered out as well.

`policy` and `negative` are verification-only. Catalog lifecycle execution
requires exactly one suite. Catalog `negative` is also verification-only.

```bash
./run_validation.sh fvt_repo_manager test
./run_validation.sh fvt_repo_manager prepare test --marker sanity
./run_validation.sh fvt_repo_manager policy verify
./run_validation.sh fvt_repo_manager catalog test --suite validate
./run_validation.sh fvt_repo_manager catalog verify --suite negative
./run_validation.sh ut_repo_manager test
```

Cleanup commands are destructive and must be selected explicitly:

```bash
./run_validation.sh fvt_repo_manager cleanup test --marker destructive
REPO_MANAGER_TEST_CLEANUP_REPO=x86_64_rhel_10.0_test_repo \
  ./run_validation.sh fvt_repo_manager cleanup_repos test \
  --marker destructive
```
