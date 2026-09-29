# test_run_config.yml — Batch Execution Reference

`test_run_config.yml` controls explicit batch runs started with:

```bash
./run_validation.sh --config
```

It selects operations; it never contains credentials. Every tracked entry is
disabled by default.

## Lifecycle order

Enabled FVT entries run in their YAML order:

1. `precheck`
2. `prepare`
3. `provision`
4. `pxeboot`
5. `cleanup`

`cleanup` is destructive, excluded from implicit full runs, and must be
enabled explicitly after reviewing cleanup policy in `test_config.yml`.
The flat `nft_orchestrator` entry runs after FVT entries when enabled.

## Entry fields

| Field | Type | Purpose |
|---|---|---|
| `run` | Boolean | Enable this entry. |
| `command` | String | `exec`, `verify`, or `test`. |
| `suite` | String | Optional registered suite beneath the tag. |
| `marker` | String | Single marker, AND (`+`), or OR (`,`) expression. |
| `dataset` | String | Optional dataset override. |
| `sync_input` | Boolean | Override Orchestrator input synchronization. |
| `sync_output` | Boolean | Override Repo Manager output synchronization. |
| `sync_image_output` | Boolean | Override Image Build Manager output synchronization. |

`test` runs `exec` followed by `verify` only when execution succeeds.
`skip_on_failure: false` attempts later enabled batch entries and reports a
non-zero aggregate result; set it to `true` to stop after the first failure.

## Registered tags and suites

| Tag | Suites |
|---|---|
| `precheck` | `environment`, `storage`, `dependencies`, `inputs` |
| `prepare` | `openchami`, `network`, `openldap` |
| `provision` | `openchami` |
| `pxeboot` | `connectivity`, `cloudinit`, `kubernetes`, `slurm`, `apptainer` |
| `cleanup` | `openchami`, `openldap`, `slurm`, `kubernetes`, `artifacts`, `credentials` |

Discover the live catalog before editing the batch file:

```bash
./run_validation.sh fvt_orchestrator list
```

## Markers

Registered markers include `sanity`, `functional`, `openldap`, `connectivity`,
`cloudinit`, `kubernetes`, `slurm`, `apptainer`, `image_download`, `negative`,
`non_disruptive`, `disruptive`, `reboot`, `scheduler_state`, and `destructive`.

Examples:

```yaml
marker: "sanity"                 # one marker
marker: "sanity,functional"      # OR
marker: "slurm+non_disruptive"   # AND
```

Unknown tags, suites, markers, commands, or incompatible fields fail before
execution. Review every enabled entry before running a batch.

## NFT entry

NFT uses one flat top-level entry rather than lifecycle subentries:

```yaml
nft_orchestrator:
  run: false
  command: "test"
  marker: ""
```

An empty marker runs all 11 NFT contracts. `performance`, `idempotency`, and
`security` select one quality area. The complete suite, performance, and
idempotency selections mutate the target; the complete suite finishes with
full cleanup. Do not enable NFT and FVT cleanup in the same unattended batch.
