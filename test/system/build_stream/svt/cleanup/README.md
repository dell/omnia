# cleanup

Back to the [test case table](../README.md).

| Order | ID | Test | Suite | Phase |
|---:|---|---|---|---|
| 4001 | `BSM_SVT_CLEANUP_E001` | `test_precheck_cleanup` | root | exec |
| 4002 | `BSM_SVT_CLEANUP_E002` | `test_run_full_domain_cleanup` | root | exec |
| 4101 | `BSM_SVT_CLEANUP_V001` | `test_postcondition_build_stream_cleanup` | `postconditions` | verify |
| 4102 | `BSM_SVT_CLEANUP_V002` | `test_postcondition_orchestrator_cleanup` | `postconditions` | verify |
| 4103 | `BSM_SVT_CLEANUP_V003` | `test_postcondition_image_build_manager_cleanup` | `postconditions` | verify |
| 4104 | `BSM_SVT_CLEANUP_V004` | `test_postcondition_repo_manager_cleanup` | `postconditions` | verify |

Destructive. Cleans every domain enabled in `test_config.yml` in this fixed
order:

| Block | Command | Flags |
|---|---|---|
| `cleanup_build_stream` | `build_stream.yml --tags cleanup` | `postgres_backup`, `cleanup_credentials` (false becomes `--skip-tags credentials`) |
| `cleanup_orchestrator` | `orchestrator.yml --tags cleanup` (`skip_approval=true` always) | `cleanup_credentials`, `cleanup_slurm`, `cleanup_k8s` |
| `cleanup_image_build_manager` | `image_build_manager.yml --tags cleanup` | `cleanup_credentials` (false becomes `--skip-tags cleanup_credentials`) |
| `cleanup_repo_manager` | `repo_manager.yml --tags cleanup_pulp` | `cleanup_logs`, `cleanup_credentials` |

**Precheck:** clears the previous exec state; at least one block enabled; the
omnia.env variables set; each enabled playbook present in the checkout.

**Exec:** right before each playbook, the paths that must survive are
recorded, so a path that never existed is not reported as deleted.
`cleanup.fail_fast` stops at the first failed playbook. Each domain's record
(flags, baseline, result) is saved to `reports/state/cleanup.json`.

**Verify:** one case per domain checks containers, units, ports, data and
credentials against its flags. Verification runs after every enabled
cleanup, so a later domain deleting data an earlier one preserved is
reported. Disabled and not-run domains are skipped.

```bash
./run_validation.sh svt_build_stream cleanup test
./run_validation.sh svt_build_stream cleanup verify --suite postconditions
```
