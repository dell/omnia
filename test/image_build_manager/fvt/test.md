Let me first re-read the current versions of the files I need to update, then read the key test files to do the full alignment check in parallel:
 
Now let me read the remaining source files needed for the alignment check:
 
Now let me check the source structure for the alignment verification:
 
Let me first read the remaining source and test files needed for a thorough alignment check and production analysis:
 
Now let me read the remaining test files and source role task files for the alignment check:
 
Now let me check the `CMDS` dict for any commands used in `build_image_func.py` that reference commands not in `common_vars.py`:
 
Let me check for any inline commands (CMDS violations) in the function file:
 
Good - all `host.run()` calls use `CMDS[...]`. Now let me check the source roles to verify full alignment, then start writing the docs:
 
Now I have full picture. Let me now rewrite both docs as generic and update the domain-specific docs. I'll batch these efficiently:
 
Now updating the README.md — the dataset section needs to reflect that datasets must be generated:
 
I need to update the README sections about dataset and setup to reflect mandatory dataset generation:
 
Now updating `test_config.md` to reflect mandatory dataset:
 
Now let me do the production readiness analysis. Let me check for issues systematically:
 
All clean. Now check for hardcoded IPs and paths:
 
Now let me check for error handling patterns and any missing `__init__.py` files:
 
All `__init__.py` files present. Now let me do the full source-to-test alignment check:
 
Let me verify the source playbook tags map to what the test CMDS and scenarios actually exercise:
 
---
 
## Summary of All Changes
 
### Files Modified
 
| File | Change |

|------|--------|

| `docs/code-style/test_automation.md` | Rewritten generic — no domain-specific examples, `<domain_name>` placeholders throughout, dataset generator marked MANDATORY |

| `docs/design/test-automation-design.md` | Rewritten generic — architecture doc with `<domain_name>` placeholders, mandatory dataset generator section (Section 4), removed all image_build_manager-specific content |

| `test/image_build_manager/README.md` | Added mandatory dataset generation steps in Setup, updated test count 12->13, rewrote Input Files section |

| `test/image_build_manager/docs/test_config.md` | Dataset field marked required, added generator instructions, removed "empty = src/ mode" as default recommendation |

| `test/image_build_manager/docs/test_run_config.md` | Added missing fields (command, dataset, sync_input, sync_output), corrected scenario descriptions |
 
---
 
## Test Code Alignment with `src/image_build_manager` — VERDICT: WELL ALIGNED
 
### Source-to-Test Coverage Matrix
 
| Source Role | Tag | Test Scenario | Tests Verify |

|-------------|-----|---------------|--------------|

| `image_build_setup` | always | Implicit (session startup) | Env vars, connectivity |

| `validate_image_build_input` | validate | `fvt/validate/` (3 TCs) | Config exists, credentials present |

| `collect_build_credentials` | always | Implicit via TC_VL_003 | Credentials file synced |

| `deploy_minio` | prepare | `fvt/prepare/container/` (8 TCs) | MinIO container, systemd, S3 buckets |

| `deploy_registry` | prepare | `fvt/prepare/container/` | Registry running, reachable |

| `fetch_build_packages` | prepare | Implicit | Packages available for build |

| `prepare_aarch64_node` | prepare | Implicit | ARM node ready |

| `build_os_images` | build | `fvt/build/` (6 TCs) | S3 images, registry images, build_status, groups |

| `cleanup_build_artifacts` | cleanup | `fvt/cleanup/` (8 TCs) | Containers, services, ports, S3, config removed |

| Full e2e | (none) | `fvt/image_build_manager/` (13 TCs) | Complete post-deploy verification |
 
**Clean checks:**

- Zero inline `host.run(f"...")` violations — all 46 calls use `CMDS[...]`

- Zero hardcoded TC IDs in test files

- Zero `print()` calls in FVT test files

- Zero hardcoded IPs in Python files

- Zero `pylint: disable` / `noqa` suppressions

- All 20 `__init__.py` files present across the module
 
---
 
## Production Readiness — Improvements Required
 
### P0 — Must Fix
 
| # | Issue | Location | Impact |

|---|-------|----------|--------|

| 1 | **UT schema path wrong** | `ut/test_validate_image_build_config.py:22-29` | `SCHEMA_DIR` resolves to `test/src/library/module_utils/...` which doesn't exist. Should be `<repo>/src/image_build_manager/plugins/module_utils/input_validation/schema`. All 6 UT tests will fail. |

| 2 | **`nft/` empty** | `test/image_build_manager/nft/` | Non-functional test directory exists but has zero tests — no performance baselines, no scalability tests |
 
### P1 — Should Fix
 
| # | Issue | Recommendation |

|---|-------|----------------|

| 3 | **No retry on transient failures** | Add retry decorator (2-3 attempts with backoff) to `run_on_host()` calls in `build_image_func.py` for SSH/network flakiness |

| 4 | **No pre-flight connectivity check** | Add a health-check step in `pytest_sessionstart` that verifies SSH and target responsiveness before syncing files |

| 5 | **Temp file cleanup on failure** | `verify_image_packages()` uses `/tmp/ibm_test_*` — if a test aborts mid-mount, files are orphaned. Wrap in `try/finally` with guaranteed cleanup |

| 6 | **No build log collection** | On playbook failure, the assert message references `{log_path}` but logs are not attached to the HTML report. Add log fetching on failure. |

| 7 | **Missing `precheck` scenario** | Source has `--tags precheck` but no test scenario for it. Add `fvt/precheck/` with env var and connectivity validation tests. |
 
### P2 — Nice to Have
 
| # | Issue | Recommendation |

|---|-------|----------------|

| 8 | **No negative tests** | Add tests for invalid input (bad config, missing credentials, wrong IP format) to verify playbook fails cleanly |

| 9 | **No idempotency tests** | Add a test that runs `--tags prepare` twice and verifies no side effects (containers not recreated, services still active) |

| 10 | **No performance baselines** | Add NFT tests: playbook duration thresholds, image build time limits, S3 upload speed checks |

| 11 | **Sequential verification** | Independent checks (S3 images, registry images, build_status) could run in parallel to reduce total test time |

| 12 | **`upgrade`/`rollback` placeholders** | Source has placeholder playbooks — when implemented, add corresponding test scenarios |
 